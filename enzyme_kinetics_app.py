# app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objs as go
from scipy.optimize import curve_fit
from io import BytesIO
import base64
import plotly.io as pio

st.set_page_config(layout="wide")
st.title("酵素キネティクス解析ツール（複数サンプル対応）")

# --- ヘルプメッセージ ---
st.sidebar.markdown("## ヘルプ")
st.sidebar.info(
    """
    - Excelファイルは次の形式：
        - A列：時間（秒）
        - B列以降：各サンプルの吸光度（列名はサンプル名）
    - ファイルをアップロード後、各列に対応する基質濃度[mM]を入力してください。
    - グラフ上で範囲をドラッグして初速度を再計算します。
    """
)

# --- サンプルExcel作成 ---
def create_sample_excel():
    time = np.arange(0, 60, 5)
    data = {
        'Time (s)': time,
        'Sample1': 0.02 + 0.008 * time,
        'Sample2': 0.01 + 0.006 * time,
        'Sample3': 0.00 + 0.004 * time
    }
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

sample_excel = create_sample_excel()
b64 = base64.b64encode(sample_excel).decode()
st.sidebar.markdown(f"[サンプルExcelをダウンロード](data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64})")

# --- ファイルアップロード ---
uploaded_file = st.file_uploader("Excelファイルをアップロード", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    if 'Time (s)' not in df.columns:
        st.error("'Time (s)' 列が必要です")
    else:
        time = df['Time (s)']
        sample_names = [col for col in df.columns if col != 'Time (s)']

        st.subheader("基質濃度の入力")
        concentrations = {}
        cols = st.columns(len(sample_names))
        for i, name in enumerate(sample_names):
            concentrations[name] = cols[i].number_input(f"{name} [mM]", value=1.0, key=f"conc_{name}")

        # --- 初速度保存用 ---
        velocities = []
        conc_list = []

        st.subheader("個別グラフと初速度の算出")
        for name in sample_names:
            absorbance = df[name]

            st.markdown(f"#### {name}")
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=time, y=absorbance, mode='lines+markers', name=name))
            fig.update_layout(
                dragmode='select',
                title='時間 vs 吸光度',
                xaxis_title='時間 (s)',
                yaxis_title='吸光度',
                height=400
            )
            selected = st.plotly_chart(fig, use_container_width=True)

            # 指定範囲から初速度計算（簡易：先頭N点）
            N = st.slider(f"{name}の初速度計算点数", 2, len(time), 5, key=f"n_{name}")
            coeffs = np.polyfit(time[:N], absorbance[:N], 1)
            velocity = coeffs[0]
            velocities.append(velocity)
            conc_list.append(concentrations[name])
            st.write(f"初速度: **{velocity:.4f} Abs/s**")

        st.subheader("重ねグラフ")
        fig_all = go.Figure()
        for name in sample_names:
            fig_all.add_trace(go.Scatter(x=time, y=df[name], mode='lines+markers', name=name))
        fig_all.update_layout(title="全サンプル吸光度 vs 時間", xaxis_title="時間 (s)", yaxis_title="吸光度")
        st.plotly_chart(fig_all, use_container_width=True)

        st.subheader("ミカエリス・メンテンプロット")
        df_result = pd.DataFrame({
            '基質濃度 [mM]': conc_list,
            '初速度 [Abs/s]': velocities
        })
        st.dataframe(df_result)

        fig_mm = go.Figure()
        fig_mm.add_trace(go.Scatter(x=conc_list, y=velocities, mode='markers+lines'))
        fig_mm.update_layout(title="初速度 vs 基質濃度", xaxis_title="[S] (mM)", yaxis_title="初速度 (Abs/s)")
        st.plotly_chart(fig_mm, use_container_width=True)

        # フィッティング
        def michaelis_menten(S, Vmax, Km):
            return (Vmax * S) / (Km + S)

        popt, _ = curve_fit(michaelis_menten, conc_list, velocities)
        Vmax, Km = popt
        st.success(f"Km = {Km:.4f} mM, Vmax = {Vmax:.4f} Abs/s")

        # --- CSV出力 ---
        csv = df_result.to_csv(index=False).encode('utf-8')
        st.download_button("解析結果をCSVでダウンロード", csv, "kinetics_results.csv", "text/csv")

        # --- PDF出力（Plotly図をPNGに変換 → PDF出力も可能） ---
        fig_bytes = pio.to_image(fig_mm, format='png')
        b64_img = base64.b64encode(fig_bytes).decode()
        href = f'<a href="data:image/png;base64,{b64_img}" download="mm_plot.png">ミカエリス・メンテングラフをPNGで保存</a>'
        st.markdown(href, unsafe_allow_html=True)

else:
    st.info("解析対象のExcelファイルをアップロードしてください。")
