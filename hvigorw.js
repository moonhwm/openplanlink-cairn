#!/usr/bin/env node
// HarmonyOS hvigor 构建脚本（命令行入口）
// 用法：node hvigorw.js [task] [--mode debug|release] [--product default]
//
// 构建环境要求：
//   1. DevEco Studio 安装路径（默认 A:\DevEco Studio）
//   2. 设置环境变量 DEVECO_STUDIO_PATH 指向 DevEco Studio 安装目录
//
// 构建步骤：
//   1. ohpm install（安装项目依赖）
//   2. hvigorw assembleHap（编译并打包 HAP）
//
// 注意：项目路径不能包含非 ASCII 字符（如中文），否则 hvigor 会报错。
//       如需在含中文路径下构建，请将项目复制到 ASCII 安全路径后再构建。

const { spawnSync } = require('child_process');
const path = require('path');
const fs = require('fs');

// JSON5 require 扩展 —— Node.js 18 不原生支持 .json5，需手动注册
require.extensions['.json5'] = function(module, filename) {
  const content = fs.readFileSync(filename, 'utf-8');
  const cleaned = content
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/\/\/.*$/gm, '')
    .replace(/,\s*([}\]])/g, '$1');
  module.exports = JSON.parse(cleaned);
};

// 查找 DevEco Studio 安装路径
function findDevEcoStudio() {
  // 1. 环境变量
  if (process.env.DEVECO_STUDIO_PATH && fs.existsSync(process.env.DEVECO_STUDIO_PATH)) {
    return process.env.DEVECO_STUDIO_PATH;
  }
  // 2. 常见安装位置
  const commonPaths = [
    'A:\\DevEco Studio',
    'C:\\Program Files\\Huawei\\DevEco Studio',
    'D:\\Program Files\\Huawei\\DevEco Studio',
    'D:\\DevEco Studio',
  ];
  for (const p of commonPaths) {
    if (fs.existsSync(p)) return p;
  }
  // 3. 从注册表读取
  try {
    const { execSync } = require('child_process');
    const regPath = execSync(
      'powershell -Command "(Get-ItemProperty \'HKLM:\\SOFTWARE\\Huawei\\DevEco Studio\').InstallPath"',
      { encoding: 'utf-8' }
    ).trim();
    if (regPath && fs.existsSync(regPath)) return regPath;
  } catch (e) { /* ignore */ }
  return null;
}

const devecoPath = findDevEcoStudio();
if (!devecoPath) {
  console.error('错误：未找到 DevEco Studio 安装路径。');
  console.error('请设置环境变量 DEVECO_STUDIO_PATH 指向 DevEco Studio 安装目录。');
  process.exit(1);
}

const nodePath = path.join(devecoPath, 'tools', 'node');
const ohpmPath = path.join(devecoPath, 'tools', 'ohpm', 'bin');
const hvigorwPath = path.join(devecoPath, 'tools', 'hvigor', 'bin', 'hvigorw.bat');
const javaPath = path.join(devecoPath, 'jbr');
const sdkPath = path.join(devecoPath, 'sdk');

// 构建环境变量
const env = {
  ...process.env,
  NODE_HOME: nodePath,
  JAVA_HOME: javaPath,
  DEVECO_SDK_HOME: sdkPath,
  PATH: `${nodePath};${ohpmPath};${javaPath}\\bin;${process.env.PATH || ''}`,
};

// 检查项目路径是否包含非 ASCII 字符
const projectPath = __dirname;
const hasNonAscii = /[^\x00-\x7F]/.test(projectPath);
if (hasNonAscii) {
  console.warn('警告：项目路径包含非 ASCII 字符，hvigor 可能无法构建。');
  console.warn('请将项目复制到仅含 ASCII 字符的路径后再构建。');
  console.warn(`当前路径: ${projectPath}`);
}

// 执行构建
const args = process.argv.slice(2);
if (args.length === 0) {
  console.log('用法: node hvigorw.js [task] [--mode debug|release] [--product default]');
  console.log('常用任务: assembleHap, clean, build');
  process.exit(0);
}

console.log(`使用 DevEco Studio: ${devecoPath}`);
console.log(`Node.js: ${path.join(nodePath, 'node.exe')}`);
console.log(`Java: ${path.join(javaPath, 'bin', 'java.exe')}`);
console.log(`SDK: ${sdkPath}`);
console.log(`任务: ${args.join(' ')}`);
console.log('');

const result = spawnSync('"' + hvigorwPath + '"', args, {
  cwd: projectPath,
  env: env,
  stdio: 'inherit',
  shell: true,
});

process.exit(result.status || 0);
