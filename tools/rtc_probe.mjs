// Cairn 席 · RTC 观看探针（Puppeteer-core 复用本机 Edge）
// 用法：node rtc_probe.mjs <auto.html 之绝对路径> [等待秒数]
// 输出：页面 console 与错误之汇总（★令牌在 auto.html 内，不入命令行、不入件）
import puppeteer from "puppeteer-core";
import { pathToFileURL } from "node:url";

const target = process.argv[2];
const waitSec = Number(process.argv[3] || 40);
const EDGE = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";

const lines = [];
const push = (s) => { lines.push(s); console.log(s); };

const browser = await puppeteer.launch({
  executablePath: EDGE,
  headless: "new",
  args: [
    "--no-sandbox", "--disable-gpu", "--autoplay-policy=no-user-gesture-required",
    "--use-fake-ui-for-media-stream", "--enable-logging=stderr", "--v=0",
  ],
});
try {
  const page = await browser.newPage();
  page.on("console", (m) => push("[console] " + m.text()));
  page.on("pageerror", (e) => push("[pageerror] " + e.message));
  page.on("requestfailed", (r) => push("[reqfail] " + r.url().slice(0, 90) + " ⇒ " + (r.failure()?.errorText || "")));
  await page.goto(pathToFileURL(target).href, { waitUntil: "load", timeout: 60000 });
  push("[goto] 已载入 " + target.split("\\").pop());
  const t0 = Date.now();
  while ((Date.now() - t0) / 1000 < waitSec) {
    await new Promise((r) => setTimeout(r, 4000));
    try {
      const log = await page.$eval("#log", (el) => el.textContent);
      const st = await page.evaluate(() => (window.__state || null));
      push("[t+" + Math.round((Date.now() - t0) / 1000) + "s] " + (st ? JSON.stringify(st) : "(无 state)"));
      const last = log.trim().split("\n").slice(-2).join(" ｜ ");
      push("   末尾日志：" + last.slice(0, 200));
    } catch (e) { push("[eval 失败] " + e.message.slice(0, 80)); }
  }
  const finalLog = await page.$eval("#log", (el) => el.textContent).catch(() => "(取不到)");
  push("═══ 页面完整日志 ═══");
  finalLog.split("\n").forEach((l) => push("  " + l));
} finally {
  await browser.close();
}
push("═══ 汇总：console " + lines.filter((l) => l.startsWith("[console]")).length
  + " 条 ｜ 错误 " + lines.filter((l) => l.startsWith("[pageerror]")).length
  + " 条 ｜ 失败请求 " + lines.filter((l) => l.startsWith("[reqfail]")).length + " 条 ═══");
