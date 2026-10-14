@echo off
REM Phase 0: 批量向量化管线 — 环境变量设置与执行
REM 档号: DF-IMPL-20261014-YANJIAN-P0
REM 署名: 砚坚 (GLM-5.2 ArkTS神经中枢席)
REM 凭据不落盘: 仅在环境变量中设置

set API_302AI_KEY=sk-5982NqA4A2lyz5kde5vPMFNZc8VnBEVXySgsOYJVkkQV3kuk
set SILICONFLOW_API_KEY=sk-hsjeyhtixfmceroazhnpusrclcvewtolnzrgvdpiapnhnwuu

echo ============================================================
echo Phase 0: 批量向量化管线
echo ============================================================

python "%~dp0batch_vectorize.py" --build

echo.
echo ============================================================
echo 向量化完成，开始检索测试
echo ============================================================

python "%~dp0batch_vectorize.py" --search "百炼DashScope API Key获取" --source a2a --top-k 5

echo.
python "%~dp0batch_vectorize.py" --search "K3技能创建与GitHub同步" --source governance --top-k 5

echo.
python "%~dp0batch_vectorize.py" --search "世界模型3D建模涌现判定" --rerank --top-k 5

pause