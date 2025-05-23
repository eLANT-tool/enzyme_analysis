import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objs as go
from scipy.optimize import curve_fit
from openpyxl import load_workbook
from io import BytesIO
import base64

# --- ヘルプ表示 ---
st.sidebar.markdown("## ヘルプ")
st.sidebar.info("""
- Excelファイルは以下の形式にしてください：
    - 1列目：時間（秒）
    - 2列目以降：各サンプルの吸光度データ（ヘッダーに濃度名を記載）
- グラフをドラッグで範囲選択し、初速度を再計算できます。
- 初速度と基質濃度からミカエリス・メンテン式を自動フィッティングします。
- 結果はCSVでダウンロードできます。
""")

# --- サンプルExcelのダウンロード機能 ---
def create_sample_excel():
    time_points = np.arange(0, 60, 5)
    df_sample = pd.DataFrame({
        'Time (s)': time_points,
        '0.5 mM': [0.02, 0.05, 0.09, 0.14, 0.18, 0.23, 0.29, 0.35, 0.40, 0.45, 0.50, 0.54],
        '1.0 mM': [0.01, 0.03, 0.07, 0.12, 0.17, 0.21, 0.28, 0.34, 0.39, 0.44, 0.48, 0.53]
    })
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_sample.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

sample_excel = create_sample_excel()
b64 = base64.b64encode(sample_excel).decode()
st.sidebar.markdown(f"[解析用Excelテンプレートをダウンロード](data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64})")

# --- タイトル ---
st.title("酵素キネティクス解析ツール")

# --- ファイルアップロード ---
uploaded_file = st.file_uploader("Excelファイルをアップロード（.xlsx）", type=["xlsx"])
if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file, engine='openpyxl')
        df.columns = [col.strip() for col in df.columns]

        time = df.iloc[:, 0]
        sample_names = df.columns[1:]

        # --- 全サンプルの重ね描きグラフ ---
        st.markdown("### 吸光度 vs 時間（全サンプル）")
        fig_all = go.Figure()
        for name in sample_names:
            fig_all.add_trace(go.Scatter(x=time, y=df[name], mode='lines+markers', name=name))
        fig_all.update_layout(
            title='吸光度の推移（複数サンプル）',
            xaxis_title='時間 (s)',
            yaxis_title='吸光度',
            height=500
        )
        st.plotly_chart(fig_all, use_container_width=True)

        velocities = []
        substrates = []

        # --- 個別グラフで範囲指定と初速度 ---
        for name in sample_names:
            st.markdown(f"---\n### サンプル: {name}")
            absorbance = df[name]

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=time, y=absorbance, mode='lines+markers', name=name))
            fig.update_layout(
                title=f'吸光度 vs 時間 - {name}',
                xaxis_title='時間 (s)',
                yaxis_title='吸光度',
                dragmode='select',
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)

            st.write("範囲選択に使うインデックスを以下で設定してください：")
            idx_range = st.slider(f"[{name}] データ範囲（インデックス）", 0, len(time) - 1, (0, 5))

            # 選択範囲を強調表示
            x_selected = time.iloc[idx_range[0]:idx_range[1]+1]
            y_selected = absorbance.iloc[idx_range[0]:idx_range[1]+1]
            coeffs = np.polyfit(x_selected, y_selected, 1)
            velocity = coeffs[0]

            st.write(f"**初速度:** {velocity:.4f} Abs/s")
            velocities.append(velocity)
            substrates.append(float(name.replace('mM', '').strip()))

        # --- 初速度 vs 基質濃度グラフ ---
        st.markdown("---\n### 初速度 vs 基質濃度")
        df_result = pd.DataFrame({
            '基質濃度 [mM]': substrates,
            '初速度 [Abs/s]': velocities
        }).sort_values(by='基質濃度 [mM]')
        st.dataframe(df_result)

        # --- 結果CSVダウンロード ---
        csv = df_result.to_csv(index=False).encode('utf-8')
        st.download_button("結果をCSVでダウンロード", csv, "result.csv", "text/csv")

    except Exception as e:
        st.error(f"ファイルの読み込み中にエラーが発生しました：{e}")
else:
    st.warning("Excelファイルをアップロードしてください。")
