/**
 * daily-trend-scan 每日追新云函数
 *
 * 功能：
 * 1. 扫描GitHub热门项目（按关键词搜索，按stars排序）
 * 2. 评估与当前项目的整合可能性（1-5评分）
 * 3. 评分≥3的项目进入待审议队列
 * 4. 报告写入Supabase总线 + 返回JSON结果
 *
 * 触发方式：CloudBase Timer（cron: 0 0 9 * * * *，每日9:00）+ HTTP 手动触发
 *
 * 环境变量：
 *   SUPABASE_URL - Supabase 项目 URL
 *   SUPABASE_ANON_KEY - Supabase 匿名密钥
 *   GITHUB_TOKEN - GitHub API Token（可选，提高速率限制）
 *
 * 输出：
 *   - 报告写入 Supabase cross_mode_channel 总线（kind=daily_trend）
 *   - 评分≥3的项目写入 kind=trend_review_queue
 *   - 返回 JSON 汇总结果
 */

const https = require('https');

const SUPABASE_URL = process.env.SUPABASE_URL || '';
const SUPABASE_ANON_KEY = process.env.SUPABASE_ANON_KEY || '';
const GITHUB_TOKEN = process.env.GITHUB_TOKEN || '';

// 默认搜索关键词
const DEFAULT_KEYWORDS = ['harmony', 'arkts', 'a2a', 'llm', 'quant'];

// 整合评估关键词权重
const RELEVANCE_KEYWORDS = {
  harmony: 2,
  arkts: 2,
  harmonyos: 2,
  a2a: 1.5,
  llm: 1,
  quant: 1.5,
  agent: 1,
  'ai-agent': 1.5,
  cloud: 0.5,
  serverless: 0.5,
  supabase: 1,
  typescript: 0.5,
};

/**
 * 统一 HTTPS 请求封装
 */
function requestHttps(url, options = {}) {
  return new Promise((resolve, reject) => {
    const urlObj = new URL(url);
    const reqOptions = {
      method: options.method || 'GET',
      hostname: urlObj.hostname,
      path: urlObj.pathname + urlObj.search,
      headers: options.headers || {},
      timeout: options.timeout || 15000,
    };
    const req = https.request(reqOptions, (res) => {
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => {
        try { resolve({ statusCode: res.statusCode, data: JSON.parse(data) }); }
        catch (e) { resolve({ statusCode: res.statusCode, data }); }
      });
    });
    req.on('error', reject);
    req.on('timeout', () => { req.destroy(); reject(new Error('request timeout')); });
    if (options.body) { req.write(JSON.stringify(options.body)); }
    req.end();
  });
}

/**
 * 写入 Supabase 总线表
 */
async function writeBusMessage(payload) {
  if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
    console.log('[daily-trend-scan] Supabase not configured, skipping bus write');
    return null;
  }
  try {
    const result = await requestHttps(`${SUPABASE_URL}/rest/v1/cross_mode_channel`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'apikey': SUPABASE_ANON_KEY,
        'Authorization': `Bearer ${SUPABASE_ANON_KEY}`,
      },
      body: payload,
    });
    return result;
  } catch (e) {
    console.error('[daily-trend-scan] Bus write error:', e.message);
    return null;
  }
}

/**
 * 搜索GitHub热门项目
 */
async function searchGitHubProjects(keyword, perPage = 10) {
  const headers = { 'User-Agent': 'daily-trend-scan' };
  if (GITHUB_TOKEN) {
    headers['Authorization'] = `token ${GITHUB_TOKEN}`;
  }

  // 搜索最近30天内创建或更新的、stars≥10的仓库
  // 注意：GitHub Search API 使用 + 分隔条件，> 表示大于，不能被encodeURIComponent编码
  const dateThreshold = new Date(Date.now() - 30 * 24 * 3600 * 1000).toISOString().split('T')[0];
  const url = `https://api.github.com/search/repositories?q=${keyword}+stars:>10+pushed:>${dateThreshold}&sort=stars&order=desc&per_page=${perPage}`;

  try {
    const result = await requestHttps(url, { method: 'GET', headers, timeout: 10000 });
    if (result.statusCode === 200 && result.data && result.data.items) {
      return result.data.items.map(repo => ({
        name: repo.full_name,
        url: repo.html_url,
        description: repo.description || '',
        stars: repo.stargazers_count,
        language: repo.language || '',
        topics: repo.topics || [],
        created_at: repo.created_at,
        updated_at: repo.updated_at,
        license: repo.license ? repo.license.spdx_id : '',
        open_issues: repo.open_issues_count,
      }));
    }
    console.log(`[daily-trend-scan] GitHub search for "${keyword}" returned status ${result.statusCode}`);
    return [];
  } catch (e) {
    console.error(`[daily-trend-scan] GitHub search error for "${keyword}": ${e.message}`);
    return [];
  }
}

/**
 * 评估整合可行性评分（1-5）
 *
 * 评分维度：
 * - 相关度（关键词匹配权重）
 * - 活跃度（最近更新时间、stars增长）
 * - 可集成性（语言兼容性、许可证兼容性）
 * - 成熟度（stars数量、issues数量）
 * - 创新性（描述中的关键词）
 */
function evaluateIntegrationScore(project) {
  let score = 0;

  // 1. 相关度评估（0-2分）
  const textToMatch = `${project.name} ${project.description} ${project.topics.join(' ')}`.toLowerCase();
  let relevanceScore = 0;
  for (const [keyword, weight] of Object.entries(RELEVANCE_KEYWORDS)) {
    if (textToMatch.includes(keyword)) {
      relevanceScore += weight;
    }
  }
  relevanceScore = Math.min(relevanceScore, 2);
  score += relevanceScore;

  // 2. 活跃度评估（0-1分）
  const updatedDate = new Date(project.updated_at);
  const daysSinceUpdate = (Date.now() - updatedDate.getTime()) / (24 * 3600 * 1000);
  if (daysSinceUpdate < 7) {
    score += 1;
  } else if (daysSinceUpdate < 30) {
    score += 0.5;
  }

  // 3. 可集成性评估（0-1分）
  // ArkTS与TypeScript高度兼容，纯ArkTS项目零三方依赖
  if (project.language === 'TypeScript' || project.language === 'ArkTS') {
    score += 1;
  } else if (project.language === 'JavaScript') {
    score += 0.5;
  } else if (project.language === 'Python') {
    // Python项目可能是量化/LLM相关，有参考价值
    score += 0.3;
  }

  // 许可证兼容性
  if (project.license === 'MIT' || project.license === 'Apache-2.0' || project.license === 'ISC') {
    score += 0.2;
  }

  // 4. 成熟度评估（0-0.5分）
  if (project.stars >= 100) {
    score += 0.5;
  } else if (project.stars >= 50) {
    score += 0.3;
  } else if (project.stars >= 10) {
    score += 0.1;
  }

  // 5. 创新性评估（0-0.5分）
  const innovativeKeywords = ['novel', 'new', 'innovative', 'breakthrough', 'state-of-art', 'cutting-edge'];
  const descLower = project.description.toLowerCase();
  for (const kw of innovativeKeywords) {
    if (descLower.includes(kw)) {
      score += 0.5;
      break;
    }
  }

  // 评分范围1-5
  return Math.max(1, Math.min(5, Math.round(score * 2.5) / 2.5));
}

/**
 * 生成整合建议
 */
function generateIntegrationAdvice(project, score) {
  if (score >= 4) {
    return '高优先级整合——与当前项目高度相关且技术兼容，建议立即进入实验队列';
  } else if (score >= 3) {
    return '中等优先级整合——有一定相关性，建议进入待审议队列';
  } else if (score >= 2) {
    return '低优先级——相关性有限，可作为参考但不建议直接整合';
  } else {
    return '不建议整合——与当前项目方向不匹配';
  }
}

/**
 * 执行扫描
 */
async function runScan(keywords) {
  const allProjects = [];
  const seenRepos = new Set();

  // 并行搜索所有关键词
  const searchPromises = keywords.map(kw => searchGitHubProjects(kw, 10));
  const searchResults = await Promise.allSettled(searchPromises);

  for (let i = 0; i < keywords.length; i++) {
    const result = searchResults[i];
    if (result.status === 'fulfilled') {
      for (const project of result.value) {
        if (!seenRepos.has(project.name)) {
          seenRepos.add(project.name);
          const score = evaluateIntegrationScore(project);
          const advice = generateIntegrationAdvice(project, score);
          allProjects.push({
            ...project,
            search_keyword: keywords[i],
            integration_score: score,
            integration_advice: advice,
          });
        }
      }
    } else {
      console.error(`[daily-trend-scan] Search for "${keywords[i]}" failed: ${result.reason}`);
    }
  }

  // 按整合评分排序
  allProjects.sort((a, b) => b.integration_score - a.integration_score);

  // 分离待审议项目（评分≥3）
  const reviewQueue = allProjects.filter(p => p.integration_score >= 3);
  const archiveProjects = allProjects.filter(p => p.integration_score < 3);

  return {
    total_found: allProjects.length,
    review_queue: reviewQueue,
    archive: archiveProjects.slice(0, 20), // 最多保留20条低分项目
    keywords_used: keywords,
  };
}

/**
 * 生成报告文本
 */
function generateReportText(scanResult, timestamp) {
  const date = new Date(timestamp).toISOString().split('T')[0];
  let report = `# 每日追新报告 ${date}\n\n`;
  report += `**执行时间**: ${new Date(timestamp).toISOString()}\n`;
  report += `**搜索关键词**: ${scanResult.keywords_used.join(', ')}\n`;
  report += `**发现项目总数**: ${scanResult.total_found}\n`;
  report += `**待审议项目（评分≥3）**: ${scanResult.review_queue.length}\n\n`;

  if (scanResult.review_queue.length > 0) {
    report += `## 待审议项目（评分≥3）\n\n`;
    for (const project of scanResult.review_queue) {
      report += `### ${project.name} — 评分 ${project.integration_score}\n`;
      report += `- **URL**: ${project.url}\n`;
      report += `- **描述**: ${project.description}\n`;
      report += `- **Stars**: ${project.stars} | **语言**: ${project.language} | **许可证**: ${project.license}\n`;
      report += `- **搜索关键词**: ${project.search_keyword}\n`;
      report += `- **整合建议**: ${project.integration_advice}\n\n`;
    }
  }

  if (scanResult.archive.length > 0) {
    report += `## 其他发现项目（评分<3，仅归档）\n\n`;
    for (const project of scanResult.archive) {
      report += `- ${project.name} (评分${project.integration_score}, ⭐${project.stars}) — ${project.description.substring(0, 80)}\n`;
    }
  }

  return report;
}

/**
 * 主入口
 */
exports.main = async (event) => {
  const action = event.action || 'scan';
  const keywords = event.keywords || DEFAULT_KEYWORDS;
  const timestamp = Date.now();

  console.log(`[daily-trend-scan] Starting scan at ${new Date(timestamp).toISOString()}, keywords=${JSON.stringify(keywords)}`);

  try {
    if (action === 'scan') {
      const scanResult = await runScan(keywords);
      const reportText = generateReportText(scanResult, timestamp);

      // 写入Supabase总线——每日追新报告
      await writeBusMessage({
        from_mode: 'yan-jian-codearts-glm52',
        to_mode: 'all',
        kind: 'daily_trend',
        payload: {
          timestamp,
          total_found: scanResult.total_found,
          review_queue_count: scanResult.review_queue.length,
          keywords: scanResult.keywords_used,
          review_queue: scanResult.review_queue.map(p => ({
            name: p.name,
            url: p.url,
            score: p.integration_score,
            advice: p.integration_advice,
          })),
          report_text: reportText,
        },
        created_at: new Date(timestamp).toISOString(),
      });

      // 评分≥3的项目写入待审议队列
      if (scanResult.review_queue.length > 0) {
        await writeBusMessage({
          from_mode: 'yan-jian-codearts-glm52',
          to_mode: 'yan-jian-codearts-glm52',
          kind: 'trend_review_queue',
          payload: {
            timestamp,
            items: scanResult.review_queue.map(p => ({
              name: p.name,
              url: p.url,
              description: p.description,
              stars: p.stars,
              language: p.language,
              license: p.license,
              score: p.integration_score,
              advice: p.integration_advice,
              search_keyword: p.search_keyword,
            })),
          },
          created_at: new Date(timestamp).toISOString(),
        });
        console.log(`[daily-trend-scan] ${scanResult.review_queue.length} items added to review queue`);
      }

      console.log(`[daily-trend-scan] Scan complete: total=${scanResult.total_found}, review_queue=${scanResult.review_queue.length}`);

      return {
        ok: true,
        timestamp,
        total_found: scanResult.total_found,
        review_queue_count: scanResult.review_queue.length,
        keywords_used: scanResult.keywords_used,
        review_queue: scanResult.review_queue,
        archive_count: scanResult.archive.length,
        report_text: reportText,
      };
    }

    return { ok: false, error: `unknown action: ${action}` };
  } catch (e) {
    console.error('[daily-trend-scan] Error:', e.message);
    return { ok: false, error: e.message };
  }
};