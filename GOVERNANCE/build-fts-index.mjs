#!/usr/bin/env node
/**
 * GOVERNANCE FTS5 全文搜索索引
 * 
 * 对 GOVERNANCE/ 目录下所有 Markdown 文档建立 SQLite FTS5 全文搜索索引。
 * 参考 Hermes Agent 的 hermes_state_fts.py 设计，但使用零三方依赖方案
 * （SQLite + FTS5 是 Node.js 内置能力，无需额外安装）。
 * 
 * 用法：
 *   node build-fts-index.mjs              # 构建索引
 *   node build-fts-index.mjs search "关键词"  # 搜索
 *   node build-fts-index.mjs stats        # 统计
 */

import { DatabaseSync } from 'node:sqlite';
import { readFileSync, readdirSync, statSync, existsSync, mkdirSync } from 'node:fs';
import { join, extname, relative, dirname } from 'node:path';

const GOVERNANCE_DIR = join(process.cwd(), 'GOVERNANCE');
const INDEX_PATH = join(process.cwd(), '.codeartsdoer', 'fts-index.db');

function ensureDir(path) {
  const dir = dirname(path);
  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true });
  }
}

function collectMarkdownFiles(dir) {
  const results = [];
  const entries = readdirSync(dir);
  for (const entry of entries) {
    const fullPath = join(dir, entry);
    const stat = statSync(fullPath);
    if (stat.isDirectory()) {
      results.push(...collectMarkdownFiles(fullPath));
    } else if (extname(entry) === '.md') {
      results.push(fullPath);
    }
  }
  return results;
}

function buildIndex() {
  ensureDir(INDEX_PATH);
  const db = new DatabaseSync(INDEX_PATH);
  
  // 创建FTS5虚拟表
  db.exec(`
    DROP TABLE IF EXISTS governance_fts;
    CREATE VIRTUAL TABLE governance_fts USING fts5(
      path,
      title,
      content,
      tokenize = 'unicode61'
    );
  `);
  
  const files = collectMarkdownFiles(GOVERNANCE_DIR);
  let count = 0;
  
  for (const file of files) {
    const content = readFileSync(file, 'utf-8');
    const relPath = relative(process.cwd(), file);
    
    // 提取标题（第一个 # 行）
    const titleMatch = content.match(/^#\s+(.+)$/m);
    const title = titleMatch ? titleMatch[1] : relPath;
    
    // 插入FTS5索引
    db.prepare('INSERT INTO governance_fts (path, title, content) VALUES (?, ?, ?)')
      .run(relPath, title, content);
    
    count++;
  }
  
  console.log(`✅ 索引构建完成: ${count} 个文档已索引`);
  console.log(`   索引位置: ${INDEX_PATH}`);
  
  db.close();
}

function search(query) {
  if (!existsSync(INDEX_PATH)) {
    console.error('❌ 索引不存在，请先运行 build-fts-index.mjs 构建索引');
    process.exit(1);
  }
  
  const db = new DatabaseSync(INDEX_PATH);
  
  // FTS5搜索，按相关性排序
  const results = db.prepare(`
    SELECT path, title, snippet(governance_fts, 2, '>>>', '<<<', '...', 20) as snippet, rank
    FROM governance_fts
    WHERE governance_fts MATCH ?
    ORDER BY rank
    LIMIT 10
  `).all(query);
  
  if (results.length === 0) {
    console.log(`未找到匹配 "${query}" 的文档`);
  } else {
    console.log(`找到 ${results.length} 个匹配文档:`);
    for (const result of results) {
      console.log(`\n📄 ${result.title}`);
      console.log(`   路径: ${result.path}`);
      console.log(`   摘要: ${result.snippet}`);
    }
  }
  
  db.close();
}

function stats() {
  if (!existsSync(INDEX_PATH)) {
    console.error('❌ 索引不存在，请先运行 build-fts-index.mjs 构建索引');
    process.exit(1);
  }
  
  const db = new DatabaseSync(INDEX_PATH);
  
  const result = db.prepare('SELECT COUNT(*) as count FROM governance_fts').get();
  console.log(`📊 索引统计:`);
  console.log(`   文档数: ${result.count}`);
  console.log(`   索引位置: ${INDEX_PATH}`);
  
  // 按目录统计
  const dirStats = db.prepare(`
    SELECT 
      CASE 
        WHEN path LIKE 'GOVERNANCE/skills/%' THEN 'skills'
        WHEN path LIKE 'GOVERNANCE/experiment/%' THEN 'experiment'
        WHEN path LIKE 'GOVERNANCE/research/%' THEN 'research'
        ELSE 'other'
      END as category,
      COUNT(*) as count
    FROM governance_fts
    GROUP BY category
   1`).all();
  
  for (const stat of dirStats) {
    console.log(`   ${stat.category}: ${stat.count} 个文档`);
  }
  
  db.close();
}

// 命令行入口
const command = process.argv[2];
if (command === 'search') {
  search(process.argv[3] || '');
} else if (command === 'stats') {
  stats();
} else {
  buildIndex();
}