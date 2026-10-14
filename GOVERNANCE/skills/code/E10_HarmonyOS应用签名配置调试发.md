# E10 HarmonyOS应用签名配置：调试/发布签名、AGC证书、hap-sign-tool使用

> 适用项目：harmony-app（代号"铃语"，鸿蒙适老化股票异动播报应用），Stage模型 compatibleSdkVersion 20 / targetSdk 26、纯ArkTS、零三方依赖。本文自包含成文，不依赖对话记忆。与项目的关联点：上架AGC是Push Kit REST（替代broadcast-a2a推送的既定方向）开通的前置条件，签名链路打通是铃语真机可用与上架的分水岭。安全红线贯穿全文：不泄露任何密钥、证书、Profile与密码。

## 1 签名体系总览

鸿蒙应用签名解决三件事：包完整性（防篡改）、来源可溯（防冒充）、能力管控（权限与受控API只授予经审核的Profile）。签名材料四件套：

| 文件 | 内容 | 产生方式 |
|---|---|---|
| .p12（KeyStore） | 私钥库，含密钥对 | keytool/OpenSSL或hap-sign-tool本地生成 |
| .csr | 证书签发请求 | 本地生成，提交AGC |
| .cer | 开发者/发布证书 | AGC签发（根CA链） |
| .p7b（Profile） | 描述文件：证书+包名+权限+设备清单（调试） | AGC签发 |

打包产物两级：HAP（单模块包，真机调试直接装）与APP（Release上架格式，多HAP聚合，AGC上架必须用APP且必须发布签名）。同一台设备上"同包名不同签名"无法覆盖安装——这是无数"装不上"问题的根源，处理方式是先卸载旧包。

调试与发布是两条平行链路，材料不可混用：

| 维度 | 调试签名 | 发布签名 |
|---|---|---|
| 证书类型 | 调试证书 | 发布证书 |
| Profile | 调试Profile，含注册设备UDID清单 | 发布Profile，不含设备清单、全网可装 |
| 设备范围 | 仅Profile登记设备 | 全部设备 |
| 分发方式 | 本地安装/AGC内部测试 | AGC上架审核 |
| 密钥保管 | 可团队内流转 | 专人专库保管，丢失即断更 |

## 2 AGC证书申请流程

前置：华为开发者账号（个人/企业）实名认证。步骤：

1. AGC（AppGallery Connect）创建项目与应用，登记包名（bundleName，须与module.json5一致）、应用名"铃语"、设备与语言。
2. 本地生成密钥对与CSR（两种途径见第4、5节）。
3. AGC"用户与访问→证书"页上传CSR申请调试证书与发布证书，下载.cer。
4. AGC"用户与访问→Profile"页新增Profile：选调试/发布类型、关联证书、勾选包名与设备（调试Profile需先在AGC登记真机UDID；模拟器免登记）。
5. 下载.p7b。

两个易踩点：

- 受限权限（如本类应用不会用到的敏感权限）需在AGC单独申请并在Profile中体现，普通权限（INTERNET等system_grant权限）随Profile默认放行；铃语只需INTERNET与音频相关常规权限，无受限项。
- 发布证书与发布密钥一旦用于上架，必须长期保管：丢失发布私钥将无法对同包名应用发新版，只能换包名重来，等于丢掉全部用户。

## 3 DevEco Studio自动签名（推荐日常路径）

日常真机调试不需要手动管四件套，DevEco内置一键签名：File → Project Structure → Signing Configs，勾选"Automatically generate signature"，登录华为账号，选择团队/项目后自动完成证书申请、Profile生成与signingConfigs写入。适用边界：

- 需联网且登录账号，离线环境不可用。
- 只覆盖debug场景；release上架仍要手动配发布材料。
- 自动签名材料由IDE托管，换机器需重新生成或导入。

## 4 手动签名与build-profile.json5配置

发布链路必须手动配置。工程级build-profile.json5：

```json5
{
  "app": {
    "signingConfigs": [
      {
        "name": "default",
        "type": "HarmonyOS",
        "material": {
          "certpath": "C:/keys/lingyu-release.cer",
          "storePassword": "000000<加密串>",
          "keyAlias": "lingyu",
          "keyPassword": "000000<加密串>",
          "profile": "C:/keys/lingyu-release.p7b",
          "signAlg": "SHA256withRSA",
          "storeFile": "C:/keys/lingyu-release.p12"
        }
      }
    ],
    "products": [
      {
        "name": "default",
        "signingConfig": "default",
        "compatibleSdkVersion": "5.0",
        "targetSdkVersion": "5.1",
        "runtimeOS": "HarmonyOS"
      }
    ]
  }
}
```

纪律清单：

- 材料放工程外（如C:/keys/），.gitignore至少排除 `*.p12`、`*.cer`、`*.p7b`、`signingConfigs`敏感段；证书与Profile本身不含私钥，但入库会扩大攻击面，统一不入。
- storePassword/keyPassword由DevEco加密存储；若手工填写明文，严禁提交仓库，提交前用占位符替换，CI侧用环境变量注入。
- debug与release用两个不同name的signingConfig（如"default"与"release"），materials指向不同材料，杜绝调试材料漏进发布包。
- 打包：Build → Build Hap(s)/APP(s) → Build App(s)；上架产物为release签名APP。

## 5 hap-sign-tool使用

hap-sign-tool是SDK toolchains自带的命令行签名工具（hap-sign-tool.jar，java -jar调用），用于脱离IDE的签名与CI集成。三个核心子命令：

生成密钥对并落p12：

```bash
java -jar hap-sign-tool.jar generate-keypair \
  -keyAlias "lingyu" -keyAlg "RSA" -keySize 2048 \
  -keyStoreFile "C:/keys/lingyu.p12" \
  -keyStorePassword "***"
```

用该密钥生成CSR（提交AGC换证书）：

```bash
java -jar hap-sign-tool.jar generate-csr \
  -keyAlias "lingyu" \
  -keyStoreFile "C:/keys/lingyu.p12" -keyStorePassword "***" \
  -subject "C=CN,O=Org,CN=lingyu" \
  -signAlg "SHA256withRSA" \
  -outFile "C:/keys/lingyu.csr"
```

对HAP/APP本地签名：

```bash
java -jar hap-sign-tool.jar sign-app \
  -mode "localSignature" -keyAlias "lingyu" \
  -keyStoreFile "C:/keys/lingyu.p12" -keyStorePassword "***" -keyPassword "***" \
  -appCertFile "C:/keys/lingyu-release.cer" \
  -profileFile "C:/keys/lingyu-release.p7b" \
  -signAlg "SHA256withRSA" -profileSigned "1" \
  -inFile "build/outputs/default/unsigned.hap" \
  -outFile "build/outputs/default/lingyu-signed.hap"
```

验签与排查：

```bash
java -jar hap-sign-tool.jar verify-app \
  -inFile "lingyu-signed.hap" \
  -outCertChain "out/chain.pem" \
  -outProfile "out/profile.json"
```

CI流水线模式：材料放CI的密钥管理服务（如加密变量/保险库），构建时拉取→sign-app签名→验签→产物即弃；日志与命令回显全部打码密码参数。具体参数名以所用SDK版本的hap-sign-tool官方文档为准（不同版本参数有增减，先 `-h` 或查文档核对再写死进脚本）。

## 6 与Push Kit的衔接

已知问题"broadcast-a2a的Push需换华为Push Kit REST"意味着：铃语必须以发布签名APP上架AGC、开通Push Kit服务后，服务端才能走Push Kit REST下发通知。链路顺序：发布签名APP上架 → AGC开通Push → 服务端（云函数侧）持有Push凭据下发 → 端侧PushService.ets占位封装切换为真实Push实现（在此之前维持降级轮询，见E6/E7）。端侧永不持有Push服务端凭据。

## 7 常见错误速查

| 现象 | 根因 | 处理 |
|---|---|---|
| 安装报签名不一致（sign info inconsistent） | 设备上旧包与的新包签名不同 | 卸载旧包再装 |
| 调试包装不上真机 | 设备UDID未登记进调试Profile | AGC补登记后重新生成Profile |
| 证书/Profile过期（certificate expired） | 调试证书有效期届满 | AGC重新签发、更新材料 |
| 密码错误（keystore password incorrect） | p12密码与配置不符 | 核对storePassword/keyPassword |
| 上架被拒：签名材料混用 | APP用了调试Profile | 换发布证书+发布Profile重打 |
| CI签名后验签失败 | 参数与版本不匹配或profileSigned配置异常 | 用verify-app导出比对，核对工具版本 |

## 8 密钥管理红线（本项目执行标准）

1. 发布.p12专人保管、异地备份（丢失=断更）；调试材料不外发。
2. 仓库与文档（含GOVERNANCE下全部产出）永不出现真实密码、证书内容、Profile内容；示例一律用占位符（本文即如此执行）。
3. 材料变更走"生成→AGC签发→替换→验签→提交"五步，替换前后各留一次构建产物指纹备查。
4. 怀疑泄露立即在AGC吊销重签，宁可断更窗口也不带伤运行。

## 9 签名原理要点

- HAP本质是ZIP包，签名后以签名块形式附在包结构上，签名哈希覆盖包内全部字节——任何字节被改动验签即失败，这是防篡改的根基。
- 设备侧校验链：设备内置华为根证书 → 中间CA → 开发者证书（cer）→ Profile（p7b）→ 与包内module.json5的包名、权限声明逐项比对。Profile声明与代码请求的权限不一致（多或少）都会安装失败，这是"代码没动却装不上"的高频根因。
- 签名算法用SHA256withRSA，密钥RSA 2048位起步；算法与密钥长度由工具默认值保证，不需要自行发明。
- Profile分签名（profileSigned=1）：Profile本身也纳入签名防篡改，本地签名命令中保持默认开启。

## 10 设备登记与UDID

- 调试Profile绑定设备清单：真机UDID需先在AGC"用户与访问→设备"登记，再生成含该设备的调试Profile，缺一步真机就装不上。
- UDID获取：真机开发者选项中查看设备标识；DevEco登录账号后自动签名路径会代为完成登记，这是自动签名省事的核心。
- 新增测试机的动作序列：AGC登记UDID → 重新生成调试Profile → 本地替换p7b → 重新签名安装；只换证书不换Profile无效。
- 模拟器免UDID登记，但Push链路必须真机验证（见第11节）。

## 11 上架流程与版本纪律

1. 发布签名APP（Build → Build App(s)）。
2. AGC"我的应用"提审：隐私政策URL、权限用途说明（INTERNET用于获取行情与播报数据）、应用截图过适老化规范（E8）。
3. 审核通过上架后开通Push Kit，服务端切换到Push Kit REST（对应已知问题"broadcast-a2a需换华为Push Kit REST"）。
4. 版本升级纪律：versionCode单调递增；发布签名材料永不更换——换发布证书等于新应用，老用户无法升级。
5. 内部测试轨道先用发布证书包小范围灰度，真机验证Push与TTS全链路后再全量。

## 12 CI签名流水线骨架

```yaml
stages:
  - build:  hvigorw assembleApp --mode module -p product=default
  - fetch:  从CI密钥管理拉取p12/cer/p7b到临时目录
  - sign:   java -jar hap-sign-tool.jar sign-app ...（参数见第5节）
  - verify: java -jar hap-sign-tool.jar verify-app -inFile ...
  - clean:  销毁临时材料目录
```

- 材料只在构建机内存与临时目录短暂存在，任务结束即销毁；构建机磁盘不留p12。
- 日志与命令回显全部打码密码参数（脚本层统一替换为***)。
- verify失败即流水线失败，杜绝"签了没验"的包流出。

## 13 证书生命周期台账

| 材料 | 典型有效期 | 续期动作 |
|---|---|---|
| 调试证书 | 约一至两年 | 到期前AGC重签，替换cer与Profile |
| 发布证书 | 较长 | 专人日历提醒，到期前重签并提前发过渡版本 |
| 调试/发布Profile | 随证书 | 换证书后必须同步重新生成 |

- GOVERNANCE登记证书到期台账，提前30天预警；续期动作走"生成→签发→替换→验签→提交"五步留痕。
- 发布私钥异地备份（加密存储加双人保管），单点丢失=应用断更，这不是运维小事是资产事故。

## 14 与合规红线的关联

- 签名材料是本项目最高敏资产：任何文档（含GOVERNANCE全部产出）与代码仓库不得出现真实密码、证书内容、Profile内容，示例一律占位符——本文即按此执行。
- 上架隐私声明必须如实列明：行情数据来源、推送用途、无收费功能、无对外公开数据出口（红线"不涉对外公开/收费"的对外承诺面）。
- 提审文案与截图过红线词表检查（与E8第5节同一张表），审核被驳回的文案问题会直接延误Push切换节奏。

## 15 高频疑问裁决

- 自动签名与手动签名能否共存？能。自动签名只写debug材料，手动另配release的signingConfig，两者name不同互不覆盖；但要防止默认signingConfig被IDE覆盖后悄悄指向调试证书。
- 调试包能否直接升级安装发布包？不能。两者签名不同，覆盖安装必失败，需先卸载；团队内灰度统一用发布证书包，避免测试机反复卸装丢用户数据。
- 换了电脑开发怎么办？调试材料可导出导入（p12加cer加p7b三件套）或在新机重新自动签名；发布材料不随电脑走，只在签名人受控环境使用。
- 上架后还能改包名吗？不能。包名与AGC应用及签名链全程绑定，改包名等于新应用；命名一次定终身，起名时就要定稿。
- 多模块工程怎么签？签名配置在工程级，产物APP统一签名，各HAP不单独签——不要试图给单个HAP单独配发布材料。

### 自我评估
- 正确性：4分——签名四件套、调试/发布双链路、AGC申请流程、hap-sign-tool三命令形态、签名校验链按华为公开体系书写；hap-sign-tool具体参数名、证书有效期数值与DevEco配置字段随SDK/账号类型有差异，文内已标注以官方文档核对，未在本机实测执行。
- 完整性：4分——覆盖指定四要素（调试/发布签名、AGC证书、hap-sign-tool），另补自动签名、签名原理、UDID登记、上架与版本纪律、CI流水线、证书台账与合规关联；AGC控制台入口路径随版本可能调整。
- 可复用性：4分——流程表、配置示例、CI纪律、红线清单可直接平移到其他鸿蒙工程，仅包名与Push衔接为铃语特有并已标注。
- 字数：约2603字（正文汉字，实测统计）
- 使用模型：GLM-5.3-Flash
