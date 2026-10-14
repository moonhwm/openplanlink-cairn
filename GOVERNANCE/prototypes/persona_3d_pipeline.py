#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later WITH SSPL-1.0
"""
人设3D建模管线 — 从人设文本到世界模型入世
档号: DF-IMPL-20261012-YANJIAN-Q4.1
署名: 砚坚 (GLM-5.2 ArkTS神经中枢席)

管线步骤:
  A. 人设文本 → 首帧图像（302.AI图像生成）
  B. 首帧图像 → 3D模型（火山引擎ImageTo3D doubao-seed3d-2-0-260328）
  C. 3D模型 → LOD三级降面（gltf-transform CLI）
  D. LOD模型 → 16:9带标记首帧（渲染+标记叠加）
  E. 带标记首帧 → 世界模型入世（百炼happyoyster-1.0-adventure）

涌现判据（三问三判据）:
  1. 输入是否为因 = 定位比 ≥3倍
  2. 是否像素保真 = 自残差/他帧残差
  3. 是否有运动 = 同坐标系帧间漂移

涌现判定门槛: L0无涌现 / L1弱涌现 / L2涌现候选 / L3不予判定
"""

import os
import json
import time
import base64
import urllib.request
import urllib.error
from typing import Dict, Optional, List, Tuple
import hashlib


class Persona3DPipeline:
    """人设3D建模管线 — 从人设文本到世界模型入世"""

    # 302.AI图像生成端点
    IMG_ENDPOINT = "https://api.302ai.cn/v1/images/generations"
    # 火山引擎ImageTo3D端点
    I2D_ENDPOINT = "https://ark.cn-beijing.volces.com/api/v3/contents/generations"
    # 百炼世界模型端点（Adventure）
    WORLD_BASE = "https://trial.cn-beijing.maas.aliyuncs.com/api/v2/apps/happyoyster-1.0-adventure/openapi/v1"

    def __init__(self):
        self.api_302ai = os.environ.get("API_302AI_KEY", "")
        self.api_volcengine = os.environ.get("VOLCENGINE_API_KEY", "")
        self.api_bailian = os.environ.get("DASHSCOPE_API_KEY", "")
        self.output_dir = os.environ.get("PERSONA_3D_OUTPUT", "GOVERNANCE/research/persona_3d")
        os.makedirs(self.output_dir, exist_ok=True)

    # ===== 步骤A: 人设文本 → 首帧图像 =====

    def generate_first_frame_image(self, persona_desc: str) -> Dict:
        """
        从人设描述文本生成首帧图像

        Args:
            persona_desc: 人设描述（如"砚坚——GLM-5.2 ArkTS神经中枢席，深色立领制服，银色数据流纹路"）

        Returns:
            {"image_url": str, "image_path": str, "prompt": str}
        """
        prompt = self._build_image_prompt(persona_desc)

        payload = json.dumps({
            "model": "dall-e-3",
            "prompt": prompt,
            "n": 1,
            "size": "1024x1024",
            "quality": "hd",
        }).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_302ai}",
        }

        try:
            req = urllib.request.Request(
                self.IMG_ENDPOINT, data=payload, headers=headers, method="POST"
            )
            resp = urllib.request.urlopen(req, timeout=60)
            body = json.loads(resp.read())

            if "data" in body and len(body["data"]) > 0:
                image_url = body["data"][0].get("url", "")
                # 下载图像到本地
                image_path = self._download_image(image_url, "first_frame")
                return {
                    "image_url": image_url,
                    "image_path": image_path,
                    "prompt": prompt,
                    "status": "ok",
                }
            else:
                return {"status": "error", "error": f"响应格式异常: {str(body)[:200]}"}

        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")[:300]
            return {"status": "error", "error": f"HTTP {e.code}: {err_body}"}
        except Exception as e:
            return {"status": "error", "error": str(e)[:300]}

    def _build_image_prompt(self, persona_desc: str) -> str:
        """构建图像生成prompt"""
        return (
            f"Full body portrait of a digital persona character: {persona_desc}. "
            f"Standing pose, facing forward, clean background, "
            f"high detail, digital art style, 16:9 aspect ratio composition, "
            f"with visible unique identifying markers on clothing."
        )

    def _download_image(self, url: str, name_prefix: str) -> str:
        """下载图像到本地（使用curl绕过SSL问题）"""
        import subprocess
        timestamp = int(time.time())
        image_path = os.path.join(self.output_dir, f"{name_prefix}_{timestamp}.png")
        try:
            result = subprocess.run(
                ["curl", "-L", "-s", "-o", image_path, url],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode == 0 and os.path.exists(image_path):
                return image_path
            else:
                return f"download_failed: curl exit {result.returncode}"
        except Exception as e:
            return f"download_failed: {str(e)[:100]}"

    # ===== 步骤B: 首帧图像 → 3D模型 =====

    def image_to_3d(self, image_path: str) -> Dict:
        """
        使用火山引擎ImageTo3D将首帧图像转为3D模型

        Args:
            image_path: 本地图像路径

        Returns:
            {"model_url": str, "model_path": str, "task_id": str}
        """
        # 读取图像并转为base64
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        # 检查图像尺寸（最小921600像素≈960x960）
        # 如果图像太小，需要放大
        image_url = f"data:image/png;base64,{image_data}"

        payload = json.dumps({
            "model": "doubao-seed3d-2-0-260328",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {"url": image_url},
                }
            ],
        }).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_volcengine}",
        }

        try:
            req = urllib.request.Request(
                self.I2D_ENDPOINT, data=payload, headers=headers, method="POST"
            )
            print(f"  [ImageTo3D] 提交请求...（预计耗时~10分钟）")
            start_time = time.time()
            resp = urllib.request.urlopen(req, timeout=900)  # 15分钟超时
            latency = time.time() - start_time
            body = json.loads(resp.read())

            # 解析响应
            if "data" in body and len(body["data"]) > 0:
                model_url = body["data"][0].get("url", "")
                # 下载3D模型
                model_path = self._download_model(model_url)
                return {
                    "model_url": model_url,
                    "model_path": model_path,
                    "latency_sec": latency,
                    "status": "ok",
                }
            else:
                return {"status": "error", "error": f"响应格式异常: {str(body)[:300]}"}

        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")[:500]
            return {"status": "error", "error": f"HTTP {e.code}: {err_body}"}
        except Exception as e:
            return {"status": "error", "error": str(e)[:300]}

    def _download_model(self, url: str) -> str:
        """下载3D模型ZIP到本地"""
        timestamp = int(time.time())
        model_path = os.path.join(self.output_dir, f"persona_3d_{timestamp}.zip")
        try:
            req = urllib.request.Request(url)
            resp = urllib.request.urlopen(req, timeout=120)
            with open(model_path, "wb") as f:
                f.write(resp.read())
            return model_path
        except Exception as e:
            return f"download_failed: {str(e)[:100]}"

    # ===== 步骤C: 3D模型 → LOD三级降面 =====

    def generate_lod(self, model_path: str) -> Dict:
        """
        使用gltf-transform生成LOD三级降面模型

        Args:
            model_path: 3D模型ZIP路径（含GLB）

        Returns:
            {"lod0_path": str, "lod1_path": str, "lod2_path": str}
        """
        # 解压ZIP获取GLB
        import zipfile
        glb_path = None
        extract_dir = os.path.join(self.output_dir, f"extracted_{int(time.time())}")
        os.makedirs(extract_dir, exist_ok=True)

        try:
            with zipfile.ZipFile(model_path, "r") as zf:
                zf.extractall(extract_dir)
            # 查找GLB文件
            for root, dirs, files in os.walk(extract_dir):
                for f in files:
                    if f.endswith(".glb"):
                        glb_path = os.path.join(root, f)
                        break
                if glb_path:
                    break
        except Exception as e:
            return {"status": "error", "error": f"解压失败: {str(e)[:200]}"}

        if not glb_path:
            return {"status": "error", "error": "ZIP中未找到GLB文件"}

        # 使用gltf-transform生成LOD三级
        lod_results = {}
        lod_configs = [
            {"level": "LOD0", "ratio": "0.16", "error": "0.001"},
            {"level": "LOD1", "ratio": "0.06", "error": "0.002"},
            {"level": "LOD2", "ratio": "0.016", "error": "0.004"},
        ]

        for config in lod_configs:
            lod_path = os.path.join(self.output_dir, f"persona_{config['level']}.glb")
            cmd = (
                f"gltf-transform simplify \"{glb_path}\" \"{lod_path}\" "
                f"--ratio {config['ratio']} --error {config['error']}"
            )
            try:
                import subprocess
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
                if result.returncode == 0:
                    lod_results[f"{config['level'].lower()}_path"] = lod_path
                else:
                    lod_results[f"{config['level'].lower()}_error"] = result.stderr[:200]
            except Exception as e:
                lod_results[f"{config['level'].lower()}_error"] = str(e)[:200]

        lod_results["status"] = "ok" if "lod0_path" in lod_results else "partial"
        return lod_results

    # ===== 步骤D: LOD模型 → 16:9带标记首帧 =====

    def render_marked_frame(self, lod_path: str, marker_text: str = "砚坚-A2A") -> Dict:
        """
        将LOD模型渲染为16:9带标记首帧

        注意：本机无Unity/Blender，使用Python trimesh+Pillow做简单渲染

        Args:
            lod_path: LOD GLB模型路径
            marker_text: 标记文本（用于定位比验证）

        Returns:
            {"frame_path": str, "marker_positions": List[Dict]}
        """
        try:
            import trimesh
            from PIL import Image, ImageDraw, ImageFont

            # 加载GLB模型
            scene = trimesh.load(lod_path)
            if isinstance(scene, trimesh.Scene):
                # 渲染场景
                png = scene.save_image(resolution=[1920, 1080])
                frame_path = os.path.join(self.output_dir, f"marked_frame_{int(time.time())}.png")
                with open(frame_path, "wb") as f:
                    f.write(png)

                # 叠加标记
                img = Image.open(frame_path)
                draw = ImageDraw.Draw(img)
                # 在四个角落添加标记（用于定位比验证）
                marker_positions = []
                corners = [
                    ("top_left", 50, 50),
                    ("top_right", img.width - 200, 50),
                    ("bottom_left", 50, img.height - 50),
                    ("bottom_right", img.width - 200, img.height - 50),
                ]
                for name, x, y in corners:
                    draw.text((x, y), marker_text, fill=(255, 255, 0))
                    marker_positions.append({"name": name, "x": x, "y": y, "text": marker_text})

                img.save(frame_path)

                return {
                    "frame_path": frame_path,
                    "marker_positions": marker_positions,
                    "status": "ok",
                }
            else:
                return {"status": "error", "error": "加载的不是Scene类型"}

        except ImportError:
            return {
                "status": "error",
                "error": "trimesh或Pillow未安装，请运行: pip install trimesh Pillow",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)[:300]}

    # ===== 步骤E: 世界模型入世（待裁五+裁六） =====

    def create_world(self, first_frame_path: str, prompt: str) -> Dict:
        """
        在百炼世界模型中创建世界（需要百炼API Key + 预算）

        Args:
            first_frame_path: 16:9带标记首帧图像路径
            prompt: 世界描述prompt（≤2000字）

        Returns:
            {"world_id": str, "build_status": str}
        """
        if not self.api_bailian:
            return {
                "status": "blocked",
                "reason": "DASHSCOPE_API_KEY未设置——待裁五（百炼预算解阻）",
                "alternative": "可使用已有10个ready世界中的合适世界",
            }

        # 读取首帧图像
        with open(first_frame_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")

        payload = json.dumps({
            "async": True,
            "perspective": "第一人称",
            "prompt": prompt[:2000],
            "firstFrameImage": f"data:image/png;base64,{image_data}",
            "creationModel": "simple",
            "uploadMode": "first_frame",
        }).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_bailian}",
        }

        try:
            req = urllib.request.Request(
                f"{self.WORLD_BASE}/worlds", data=payload, headers=headers, method="POST"
            )
            resp = urllib.request.urlopen(req, timeout=30)
            body = json.loads(resp.read())
            return {
                "world_id": body.get("data", {}).get("encryptedWorldId", ""),
                "build_status": body.get("data", {}).get("status", ""),
                "status": "ok",
            }
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")[:300]
            return {"status": "error", "error": f"HTTP {e.code}: {err_body}"}
        except Exception as e:
            return {"status": "error", "error": str(e)[:300]}

    def list_existing_worlds(self) -> Dict:
        """列出已有的世界（只读面，不需要预算）"""
        if not self.api_bailian:
            return {
                "status": "blocked",
                "reason": "DASHSCOPE_API_KEY未设置",
                "known_worlds": 10,  # 沈铎席实测：10个ready世界
            }

        headers = {
            "Authorization": f"Bearer {self.api_bailian}",
        }

        try:
            req = urllib.request.Request(
                f"{self.WORLD_BASE}/worlds?page=1&pageSize=20",
                headers=headers,
                method="GET",
            )
            resp = urllib.request.urlopen(req, timeout=15)
            body = json.loads(resp.read())
            worlds = body.get("data", {}).get("worlds", [])
            return {
                "worlds": worlds,
                "count": len(worlds),
                "status": "ok",
            }
        except urllib.error.HTTPError as e:
            return {"status": "error", "error": f"HTTP {e.code}"}
        except Exception as e:
            return {"status": "error", "error": str(e)[:300]}

    # ===== 涌现判定 =====

    def evaluate_emergence(
        self,
        first_frame_path: str,
        artifact_frame_paths: List[str],
    ) -> Dict:
        """
        涌现判定 — 三问三判据

        Args:
            first_frame_path: 输入首帧（带标记）
            artifact_frame_paths: 世界模型产物帧列表

        Returns:
            {
                "locating_ratio": float,    # 判据1: 定位比 (≥3倍为阳性)
                "pixel_fidelity": float,    # 判据2: 自残差/他帧残差比 (1.0为非保真)
                "frame_drift_px": float,    # 判据3: 帧间漂移像素 (≤0.4px为无运动)
                "emergence_level": str,     # L0/L1/L2/L3
                "conclusion": str,
            }
        """
        try:
            from PIL import Image
            import numpy as np

            # 加载首帧
            first_frame = np.array(Image.open(first_frame_path).convert("L"), dtype=np.float64)

            # 判据1: 定位比 — 标记在产物帧中的定位精度与随机猜测的比值
            # 需要检测产物帧中标记的位置
            locating_ratios = []
            for artifact_path in artifact_frame_paths:
                artifact = np.array(Image.open(artifact_path).convert("L"), dtype=np.float64)
                # 简化：计算首帧与产物帧的互相关峰值位置
                if artifact.shape == first_frame.shape:
                    corr = np.fft.ifft2(
                        np.fft.fft2(first_frame) * np.conj(np.fft.fft2(artifact))
                    ).real
                    peak_pos = np.unravel_index(np.argmax(corr), corr.shape)
                    center = (first_frame.shape[0] // 2, first_frame.shape[1] // 2)
                    drift = np.sqrt((peak_pos[0] - center[0]) ** 2 + (peak_pos[1] - center[1]) ** 2)
                    # 定位比 = 画面尺寸 / 漂移距离（漂移越小定位比越大）
                    frame_size = first_frame.shape[0] * first_frame.shape[1]
                    if drift > 0:
                        locating_ratios.append(frame_size / (drift * drift))
                    else:
                        locating_ratios.append(float("inf"))

            avg_locating_ratio = np.mean(locating_ratios) if locating_ratios else 0

            # 判据2: 像素保真 — 自残差/他帧残差
            self_residuals = []
            other_residuals = []
            for i, artifact_path in enumerate(artifact_frame_paths):
                artifact = np.array(Image.open(artifact_path).convert("L"), dtype=np.float64)
                if artifact.shape == first_frame.shape:
                    self_residual = np.mean(np.abs(artifact - first_frame))
                    self_residuals.append(self_residual)
                    # 他帧残差：与其他产物帧的差异
                    for j, other_path in enumerate(artifact_frame_paths):
                        if i != j:
                            other = np.array(Image.open(other_path).convert("L"), dtype=np.float64)
                            if other.shape == artifact.shape:
                                other_residual = np.mean(np.abs(artifact - other))
                                other_residuals.append(other_residual)

            avg_self_residual = np.mean(self_residuals) if self_residuals else 0
            avg_other_residual = np.mean(other_residuals) if other_residuals else 1
            pixel_fidelity_ratio = avg_self_residual / avg_other_residual if avg_other_residual > 0 else 1.0

            # 判据3: 帧间漂移 — 同坐标系连续帧间漂移
            drifts = []
            for i in range(len(artifact_frame_paths) - 1):
                a1 = np.array(Image.open(artifact_frame_paths[i]).convert("L"), dtype=np.float64)
                a2 = np.array(Image.open(artifact_frame_paths[i + 1]).convert("L"), dtype=np.float64)
                if a1.shape == a2.shape:
                    drift = np.mean(np.abs(a1 - a2))
                    drifts.append(drift)

            avg_drift = np.mean(drifts) if drifts else 0

            # 综合判定
            j1_pass = avg_locating_ratio >= 3.0
            j2_pass = pixel_fidelity_ratio < 1.0  # 自残差 < 他帧残差 = 保真
            j3_pass = avg_drift > 0.4  # 漂移 > 0.4px = 有运动

            if not j1_pass and not j2_pass and not j3_pass:
                level = "L0"
                conclusion = "本轮未观测到涌现"
            elif j1_pass and not j2_pass and not j3_pass:
                level = "L1"
                conclusion = "弱涌现——首帧条件生效，但无保真无运动"
            elif j1_pass and (j2_pass or j3_pass):
                level = "L2"
                conclusion = "涌现候选——首帧条件生效且存在保真或运动"
            else:
                level = "L3"
                conclusion = "不予判定——判定权属主权人与他席"

            return {
                "locating_ratio": float(avg_locating_ratio),
                "pixel_fidelity_ratio": float(pixel_fidelity_ratio),
                "frame_drift_px": float(avg_drift),
                "j1_input_as_cause": j1_pass,
                "j2_pixel_fidelity": j2_pass,
                "j3_motion": j3_pass,
                "emergence_level": level,
                "conclusion": conclusion,
                "n_artifact_frames": len(artifact_frame_paths),
            }

        except ImportError:
            return {
                "status": "error",
                "error": "numpy或Pillow未安装，请运行: pip install numpy Pillow",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)[:300]}

    # ===== 完整管线 =====

    def run_full_pipeline(self, persona_desc: str) -> Dict:
        """
        运行完整人设3D建模→世界模型入世管线

        Args:
            persona_desc: 人设描述文本

        Returns:
            完整管线产出
        """
        results = {"persona_desc": persona_desc, "steps": {}}

        # 步骤A: 人设文本 → 首帧图像
        print("[步骤A] 人设文本 → 首帧图像...")
        step_a = self.generate_first_frame_image(persona_desc)
        results["steps"]["A_image_generation"] = step_a
        if step_a.get("status") != "ok":
            return results

        # 步骤B: 首帧图像 → 3D模型
        print("[步骤B] 首帧图像 → 3D模型（~10分钟）...")
        step_b = self.image_to_3d(step_a["image_path"])
        results["steps"]["B_image_to_3d"] = step_b
        if step_b.get("status") != "ok":
            return results

        # 步骤C: 3D模型 → LOD三级降面
        print("[步骤C] 3D模型 → LOD三级降面...")
        step_c = self.generate_lod(step_b["model_path"])
        results["steps"]["C_lod_generation"] = step_c

        # 步骤D: LOD模型 → 16:9带标记首帧
        if "lod0_path" in step_c:
            print("[步骤D] LOD模型 → 16:9带标记首帧...")
            step_d = self.render_marked_frame(step_c["lod0_path"])
            results["steps"]["D_marked_frame"] = step_d

        # 步骤E: 世界模型入世（待裁五+裁六）
        print("[步骤E] 世界模型入世...")
        step_e = self.create_world(
            results["steps"].get("D_marked_frame", {}).get("frame_path", ""),
            persona_desc,
        )
        results["steps"]["E_world_creation"] = step_e

        return results


# ===== 测试 =====
if __name__ == "__main__":
    # 凭据从环境变量读取，不落盘
    # 请设置: API_302AI_KEY
    if not os.environ.get("API_302AI_KEY"):
        print("⚠ 请先设置环境变量 API_302AI_KEY")
        sys.exit(1)

    pipeline = Persona3DPipeline()

    # 砚坚席位人设描述
    persona = "砚坚——GLM-5.2 ArkTS神经中枢席，深色立领制服，胸前有银色数据流纹路，左手持天平（核验），右手持放大镜（审查），下摆有数据流带（转述）"

    print("=" * 60)
    print("人设3D建模管线 — 步骤A测试（图像生成）")
    print("=" * 60)
    result_a = pipeline.generate_first_frame_image(persona)
    print(f"  status: {result_a.get('status')}")
    if result_a.get("status") == "ok":
        print(f"  image_url: {result_a['image_url'][:80]}...")
        print(f"  image_path: {result_a['image_path']}")
        print(f"  prompt: {result_a['prompt'][:100]}...")
    else:
        print(f"  error: {result_a.get('error', '')[:200]}")

    print()
    print("=" * 60)
    print("人设3D建模管线 — 步骤E测试（世界模型列表）")
    print("=" * 60)
    result_e = pipeline.list_existing_worlds()
    print(f"  status: {result_e.get('status')}")
    if result_e.get("status") == "ok":
        print(f"  count: {result_e['count']}")
        for w in result_e.get("worlds", [])[:3]:
            print(f"    {w.get('name', '?')}: {w.get('status', '?')}")
    else:
        print(f"  detail: {str(result_e)[:200]}")