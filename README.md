# 酵素キネティクス解析アプリ（Streamlit + Plotly）

このアプリは、Excelファイルを読み込み、各サンプルの吸光度データから初速度を手動選択により求め、ミカエリス・メンテンプロットを描画・解析するツールです。

## 🚀 特徴

- 吸光度 vs 時間のグラフを複数サンプルで重ねて表示
- 個別サンプルごとに範囲選択による初速度計算が可能（インデックス指定）
- 初速度 vs 基質濃度のプロットと、ミカエリス・メンテン式によるフィッティング
- 結果CSVのダウンロード
- 使いやすいインターフェースと説明付きのサイドバー
- サンプルExcelファイルのダウンロード機能付き

## 📦 インストール方法

```bash
git clone https://github.com/yourusername/enzyme-kinetics-app.git
cd enzyme-kinetics-app
pip install -r requirements.txt
streamlit run main.py
