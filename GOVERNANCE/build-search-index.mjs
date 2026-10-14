#!/usr/bin/env node
/**
 * GOVERNANCE 全文搜索索引（纯JavaScript实现，零依赖）
 * 
 * 对 GOVERNANCE/ 目录下所有 Markdown 文档建立全文搜索索引。
 * 参考 Hermes Agent 的 hermes_state_fts.py 设计，但使用纯 JavaScript 实现，
 * 不依赖 SQLite/FTS5，符合零三方依赖约束。
 * 
 * 用法：
 *   node build-search-index.mjs              # 构建索引
 *   node build-search-index.mjs search "关键词"  # 搜索
 *   node build-search-index.mjs stats        # 统计
 */

import { readFileSync, readdirSync, statSync, existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { join, extname, relative, dirname } from 'node:path';

const GOVERNANCE_DIR = join(process.cwd(), 'GOVERNANCE');
const INDEX_PATH = join(process.cwd(), '.codeartsdoer', 'search-index.json');

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

// 简单的分词器——按非字母数字字符分割，转小写
function tokenize(text) {
  return text.toLowerCase()
    .split(/[^\p{L}\p{N}]+/u)
    .filter(token => token.length > 1);
}

// 构建倒排索引
function buildInvertedIndex(documents) {
  const index = new Map(); // token -> [{path, positions}]
  for (const doc of documents) {
    const tokens = tokenize(doc.content);
    const tokenPositions = new Map(); // token -> [positions]
    for (let i = 0; i < tokens.length; i++) {
      const token = tokens[i];
      if (!tokenPositions.has(token)) {
        tokenPositions.set(token, []);
      }
      tokenPositions.get(token).push(i);
    }
    for (const [token, positions] of tokenPositions) {
      if (!index.has(token)) {
        index.set(token, []);
      }
      index.get(token).push({ path: doc.path, title: doc.title, count: positions.length });
    }
  }
  return index;
}

function buildIndex() {
  ensureDir(INDEX_PATH);
  const files = collectMarkdownFiles(GOVERNANCE_DIR);
  const documents = [];
  
  for (const file of files) {
    const content = readFileSync(file, 'utf-8');
    const relPath = relative(process.cwd(), file);
    const titleMatch = content.match(/^#\s+(.+)$/m);
    const title = titleMatch ? titleMatch[1] : relPath;
    documents.push({ path: relPath, title, content });
  }
  
  const invertedIndex = buildInvertedIndex(documents);
  
  // 序列化索引（Map -> Object）
  const serializableIndex = {};
  for (const [token, postings] of invertedIndex) {
    serializableIndex[token] = postings;
  }
  
  const indexData = {
    version: 1,
    built_at: new Date().toISOString(),
    document_count: documents.length,
    token_count: Object.keys(serializableIndex).length,
    documents: documents.map(d => ({ path: d.path, title: d.title })),
    inverted_index: serializableIndex
  };
  
  writeFileSync(INDEX_PATH, JSON.stringify(indexData, null, 2), 'utf-8');
  
  console.log(`✅ 索引构建完成: ${documents.length} 个文档, ${Object.keys(serializableIndex).length} 个唯一token`);
  console.log(`   索引位置: ${INDEX_PATH}`);
}

function search(query) {
  if (!existsSync(INDEX_PATH)) {
    console.error('❌ 索引不存在，请先运行 build-search-index.mjs 构建索引');
    process.exit(1);
  }
  
  const indexData = JSON.parse(readFileSync(INDEX_PATH, 'utf-8'));
  const queryTokens = tokenize(query);
  
  if (queryTokens.length === 0) {
    console.log('请提供搜索关键词');
    return;
  }
  
  // 对每个query token查找匹配文档，计算综合得分
  const docScores = new Map(); // path -> {title, score, matchedTokens}
  
  for (const qToken of queryTokens) {
    const postings = indexData.inverted_index[qToken];
    if (postings) {
      for (const posting of postings) {
        if (!docScores.has(posting.path)) {
          docScores.set(posting.path, { title: posting.title, score: 0, matchedTokens: [] });
        }
        const doc = docScores.get(posting.path);
        doc.score += posting.count;
        doc.matchedTokens.push(qToken);
      }
    }
  }
  
  // 按得分排序
  const results = [...docScores.entries()]
    .sort((a, b) => b[1].score - a[1].score)
    .slice(0, 10);
  
  if (results.length === 0) {
    console.log(`未找到匹配 "${query}" 的文档`);
  } else {
    console.log(`找到 ${results.length} 个匹配文档 (搜索: "${query}", tokens: [${queryTokens.join(', ')}]):`);
    for (const [path, info] of results) {
      console.log(`\n📄 ${info.title}`);
      console.log(`   路径: ${path}`);
      console.log(`   得分: ${info.score} (匹配: ${info.matchedTokens.join(', ')})`);
    }
  }
}

function stats() {
  if (!existsSync(INDEX_PATH)) {
    console.error('❌ 索引不存在，请先运行 build-search-index.mjs 构建索引');
    process.exit(1);
  }
  
  const indexData = JSON.parse(readFileSync(INDEX_PATH, 'utf-8'));
  console.log(`📊 索引统计:`);
  console.log(`   文档数: ${indexData.document_count}`);
  console.log(`   唯一token数: ${indexData.token_count}`);
  console.log(`   构建时间: ${indexData.built_at}`);
  console.log(`   索引位置: ${INDEX_PATH}`);
  
  // 按目录统计
  const categories = {};
  for (const doc of indexData.documents) {
    let category = 'other';
    if (doc.path.includes('skills/')) category = 'skills';
    else if (doc.path.includes('experiment/')) category = 'experiment';
    else if (doc.path.includes('research/')) category = 'research';
    categories[category] = (categories[category] || 0) + 1;
  }
  for (const [cat, count] of Object.entries(categories)) {
    console.log(`   ${cat}: ${count} 个文档`);
  }
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