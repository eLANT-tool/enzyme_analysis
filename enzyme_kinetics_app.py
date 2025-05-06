import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objs as go
from scipy.optimize import curve_fit
from io import BytesIO
import base64

# --- ヘルプメッセージ ---
st.sidebar.markdown("## ヘルプ")
st.sidebar.info(
    """
    - Excelファイルは以下の形式にしてください：
        - 1列目：時間（秒）
        - 2列目以降：各サンプルの吸光度データ（ヘッダーに濃度名を記載）
    - グラフをドラッグで範囲選択し、初速度を再計算できます。
    - 初速度と基質濃度からミカエリス・メンテン式を自動フィッティングします。
    - 結果はCSVでダウンロードできます。
    """
)

# --- サンプルExcelのダウンロード機能 ---
def create_sample_excel():
    time_points = np.arange(0, 60, 5)
    df_sample = pd.DataFrame({
        'Time (s)': time_points,
        '0.5 mM': [0.02, 0.05, 0.09, 0.14, 0.18, 0.23, 0.29, 0.35, 0.40, 0.45, 0.50, 0.54],
        '1.0 mM': [0.01, 0.03, 0.07, 0.12, 0.17, 0.21, 0.28, 0.34, 0.39, 0.44, 0.48, 0.53]
    })
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_sample.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

sample_excel = create_sample_excel()
b64 = base64.b64encode(sample_excel).decode()
st.sidebar.markdown(f"[解析用Excelテンプレートをダウンロード](data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64})")

# --- タイトル表示 ---
st.title("酵素キネティクス解析ツール（Plotly対応・初速度選択可能）")

# --- ファイルアップロード ---
uploaded_file = st.file_uploader("Excelファイルをアップロード（1列目は時間、2列目以降は吸光度）", type=["xlsx", "xls"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
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
            dragmode='zoom',
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
            selected = st.plotly_chart(fig, use_container_width=True)

            st.write("範囲選択に使うインデックスを以下で設定してください：")
            idx_range = st.slider(f"[{name}] データ範囲（インデックス）", 0, len(time)-2, (0, 5))

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

        fig_rate = go.Figure()
        fig_rate.add_trace(go.Scatter(
            x=df_result['基質濃度 [mM]'],
            y=df_result['初速度 [Abs/s]'],
            mode='markers+lines',
            name='初速度'
        ))
        fig_rate.update_layout(
            title='ミカエリス・メンテンプロット',
            xaxis_title='基質濃度 [mM]',
            yaxis_title='初速度 [Abs/s]'
        )
        st.plotly_chart(fig_rate, use_container_width=True)

        # --- Michaelis-Menten フィッティング ---
        def michaelis_menten(S, Vmax, Km):
            return (Vmax * S) / (Km + S)

        # 欠損値・無限値を除く
        df_valid = df_result.replace([np.inf, -np.inf], np.nan).dropna()

        if len(df_valid) >= 3:
            try:
                popt, _ = curve_fit(
                    michaelis_menten,
                    df_valid['基質濃度 [mM]'],
                    df_valid['初速度 [Abs/s]'],
                    bounds=(0, np.inf)
                )
                Vmax, Km = popt
                st.success(f"Vmax = {Vmax:.4f} Abs/s, Km = {Km:.4f} mM")
            except Exception as e:
                st.error(f"フィッティングに失敗しました：{e}")
        else:
            st.warning("有効なデータが少なすぎてフィッティングできません（最低3点必要）")

        # --- 結果CSVダウンロード ---
        csv = df_result.to_csv(index=False).encode('utf-8')
        st.download_button("結果をCSVでダウンロード", csv, "result.csv", "text/csv")

    except Exception as e:
        st.error(f"ファイルの読み込み中にエラーが発生しました：{e}")
else:
    st.warning("Excelファイルをアップロードしてください。")
