/**
 * A2A Node Registry - Global Registration Center
 * Deployed on Huan16 (120.46.86.165)
 * 
 * Provides:
 *   POST /nodes/register    - Register a new node
 *   GET  /nodes             - Query all online nodes
 *   GET  /nodes/:nodeId     - Query specific node
 *   POST /nodes/heartbeat   - Heartbeat renewal
 *   POST /nodes/unregister  - Unregister a node
 *   GET  /health            - Health check
 * 
 * Auto-timeout: nodes without heartbeat for 30s → offline
 * 
 * Spec: GOVERNANCE/proposals/a2a_node_discovery_20261005.md
 */

import { createServer } from 'http';
import { createHash } from 'crypto';

const PORT = process.env.NODE_REGISTRY_PORT || 4174;
const HOST = process.env.NODE_REGISTRY_HOST || '0.0.0.0';
const HEARTBEAT_TIMEOUT_MS = 30000; // 30 seconds
const CLEANUP_INTERVAL_MS = 5000;   // Check every 5 seconds

// In-memory node registry
const nodes = new Map();

// Cleanup timer - mark nodes as offline if heartbeat expired
setInterval(() => {
  const now = Date.now();
  for (const [nodeId, node] of nodes) {
    if (node.status === 'online' || node.status === 'busy') {
      const elapsed = now - node.lastHeartbeatMs;
      if (elapsed > HEARTBEAT_TIMEOUT_MS) {
        node.status = 'offline';
        node.offlineReason = 'heartbeat_timeout';
        node.offlineAt = new Date().toISOString();
        console.log(`[TIMEOUT] Node ${nodeId} marked offline (no heartbeat for ${elapsed}ms)`);
      }
    }
  }
}, CLEANUP_INTERVAL_MS);

// HTTP server
const server = createServer((req, res) => {
  // CORS headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, X-Seat-Id, X-Seat-Sig');
  
  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  const url = new URL(req.url, `http://${HOST}:${PORT}`);
  const path = url.pathname;
  const method = req.method;

  // Health check
  if (path === '/health' && method === 'GET') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      ok: true,
      service: 'a2a-node-registry',
      version: '0.1.0',
      nodesTotal: nodes.size,
      nodesOnline: [...nodes.values()].filter(n => n.status === 'online').length,
      timestamp: new Date().toISOString()
    }));
    return;
  }

  // Parse JSON body for POST requests
  if (method === 'POST') {
    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', () => {
      try {
        const data = body ? JSON.parse(body) : {};
        handlePost(path, data, req, res);
      } catch (e) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'invalid_json', message: e.message }));
      }
    });
    return;
  }

  // GET routes
  if (method === 'GET') {
    if (path === '/nodes') {
      const nodeList = [...nodes.values()].map(n => ({
        nodeId: n.nodeId,
        seatName: n.seatName,
        endpoint: n.endpoint,
        capabilities: n.capabilities,
        status: n.status,
        lastHeartbeat: n.lastHeartbeat,
        macAddress: n.macAddress ? n.macAddress : undefined,
        offlineReason: n.offlineReason
      }));
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({
        ok: true,
        count: nodeList.length,
        online: nodeList.filter(n => n.status === 'online').length,
        nodes: nodeList
      }));
      return;
    }

    // GET /nodes/:nodeId
    const nodeMatch = path.match(/^\/nodes\/(.+)$/);
    if (nodeMatch) {
      const nodeId = decodeURIComponent(nodeMatch[1]);
      const node = nodes.get(nodeId);
      if (node) {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ ok: true, node }));
      } else {
        res.writeHead(404, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'node_not_found', nodeId }));
      }
      return;
    }
  }

  // 404
  res.writeHead(404, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ error: 'not_found', path }));
});

function handlePost(path, data, req, res) {
  // POST /nodes/register
  if (path === '/nodes/register') {
    const { nodeId, seatName, endpoint, capabilities, macAddress } = data;
    if (!nodeId || !seatName) {
      res.writeHead(400, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'missing_fields', required: ['nodeId', 'seatName'] }));
      return;
    }
    
    const now = Date.now();
    const node = {
      nodeId,
      seatName,
      endpoint: endpoint || '',
      capabilities: capabilities || [],
      status: 'online',
      macAddress: macAddress || '',
      registeredAt: new Date(now).toISOString(),
      lastHeartbeat: new Date(now).toISOString(),
      lastHeartbeatMs: now,
      offlineReason: null,
      offlineAt: null
    };
    
    const wasOffline = nodes.has(nodeId) && nodes.get(nodeId).status === 'offline';
    nodes.set(nodeId, node);
    
    console.log(`[REGISTER] Node ${nodeId} (${seatName}) registered${wasOffline ? ' (recovery from offline)' : ''}`);
    
    // Return current online nodes for discovery
    const onlineNodes = [...nodes.values()]
      .filter(n => n.status === 'online' && n.nodeId !== nodeId)
      .map(n => ({
        nodeId: n.nodeId,
        seatName: n.seatName,
        endpoint: n.endpoint,
        capabilities: n.capabilities,
        status: n.status
      }));
    
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      ok: true,
      nodeId,
      status: 'online',
      discoveredNodes: onlineNodes,
      discoveredCount: onlineNodes.length
    }));
    return;
  }

  // POST /nodes/heartbeat
  if (path === '/nodes/heartbeat') {
    const { nodeId, status } = data;
    if (!nodeId) {
      res.writeHead(400, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'missing_fields', required: ['nodeId'] }));
      return;
    }
    
    const node = nodes.get(nodeId);
    if (!node) {
      res.writeHead(404, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'node_not_found', nodeId, hint: 'call /nodes/register first' }));
      return;
    }
    
    const now = Date.now();
    node.lastHeartbeatMs = now;
    node.lastHeartbeat = new Date(now).toISOString();
    if (status && ['online', 'busy'].includes(status)) {
      node.status = status;
    }
    node.offlineReason = null;
    node.offlineAt = null;
    
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      ok: true,
      nodeId,
      status: node.status,
      lastHeartbeat: node.lastHeartbeat
    }));
    return;
  }

  // POST /nodes/unregister
  if (path === '/nodes/unregister') {
    const { nodeId, reason } = data;
    if (!nodeId) {
      res.writeHead(400, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'missing_fields', required: ['nodeId'] }));
      return;
    }
    
    const node = nodes.get(nodeId);
    if (!node) {
      res.writeHead(404, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'node_not_found', nodeId }));
      return;
    }
    
    node.status = 'offline';
    node.offlineReason = reason || 'manual_unregister';
    node.offlineAt = new Date().toISOString();
    
    console.log(`[UNREGISTER] Node ${nodeId} (${node.seatName}) unregistered: ${node.offlineReason}`);
    
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      ok: true,
      nodeId,
      status: 'offline',
      offlineReason: node.offlineReason
    }));
    return;
  }

  // Unknown POST route
  res.writeHead(404, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ error: 'not_found', path, method: 'POST' }));
}

server.listen(PORT, HOST, () => {
  console.log(`[A2A Node Registry] Listening on ${HOST}:${PORT}`);
  console.log(`[A2A Node Registry] Heartbeat timeout: ${HEARTBEAT_TIMEOUT_MS}ms`);
  console.log(`[A2A Node Registry] Cleanup interval: ${CLEANUP_INTERVAL_MS}ms`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('[A2A Node Registry] SIGTERM received, shutting down...');
  server.close(() => {
    console.log('[A2A Node Registry] Server closed.');
    process.exit(0);
  });
});

process.on('SIGINT', () => {
  console.log('[A2A Node Registry] SIGINT received, shutting down...');
  server.close(() => {
    console.log('[A2A Node Registry] Server closed.');
    process.exit(0);
  });
});