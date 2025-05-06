# enzyme_kinetics_app_v2.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from scipy.optimize import curve_fit
from io import BytesIO
import base64

# --- ヘルプメッセージ ---
st.sidebar.markdown("## ヘルプ")
st.sidebar.info(
    """
    - Excelファイルは次の形式でアップロードしてください：
      - A列：時間（秒）
      - B列以降：各列に異なる基質濃度の吸光度（例：0.5mM, 1.0mM, ...）
    - サンプルExcelをダウンロードし、そこにご自身のデータを貼り付けて使ってください。
    - グラフはドラッグで範囲選択できます。初速度は選択範囲で再計算されます。
    """
)

# --- サンプルExcelの作成とダウンロード ---
def create_sample_excel():
    time = np.arange(0, 60, 5)
    data = {
        'Time (s)': time,
        '0.5 mM': 0.02 + 0.007 * time,
        '1.0 mM': 0.03 + 0.010 * time,
        '2.0 mM': 0.04 + 0.014 * time
    }
    df_sample = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_sample.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

sample_excel = create_sample_excel()
b64 = base64.b64encode(sample_excel).decode()
st.sidebar.markdown(f"[解析用Excelテンプレートをダウンロード](data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64})")

# --- タイトル ---
st.title("酵素キネティクス解析ツール（範囲選択・ドラッグ対応）")

# --- ファイルアップロード ---
uploaded_file = st.file_uploader("Excelファイルをアップロード（時間＋複数濃度の吸光度列）", type=["xlsx", "xls"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    df.columns = [str(col).strip() for col in df.columns]

    if 'Time (s)' not in df.columns:
        st.error("A列に 'Time (s)' 列が必要です。")
    else:
        time = df['Time (s)']
        concentrations = [col for col in df.columns if col != 'Time (s)']

        velocity_data = []

        for conc in concentrations:
            absorbance = df[conc]

            # グラフ描画
            st.subheader(f"吸光度 vs 時間: {conc}")
            fig = px.scatter(x=time, y=absorbance, labels={'x': '時間 (s)', 'y': '吸光度'})
            fig.update_traces(mode='lines+markers')
            fig.update_layout(dragmode='select')
            fig.update_layout(height=500)
            fig.add_trace(go.Scatter(x=time, y=absorbance, mode='lines+markers', name=conc))
            selected_range = st.plotly_chart(fig, use_container_width=True)

            st.markdown(f"#### 初速度推定（{conc}）")
            N = st.slider(f"{conc} の線形近似に使う点数", min_value=2, max_value=len(time), value=5, key=conc)
            coeffs = np.polyfit(time[:N], absorbance[:N], 1)
            init_velocity = coeffs[0]
            st.write(f"**初速度:** {init_velocity:.4f} Abs/s")

            velocity_data.append((float(conc.replace('mM', '').strip()), init_velocity))

        # --- ミカエリス・メンテンプロット ---
        if velocity_data:
            st.subheader("ミカエリス・メンテンプロット")
            substrate_concs, velocities = zip(*sorted(velocity_data))
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=substrate_concs,
                y=velocities,
                mode='markers+lines',
                name='初速度'
            ))
            fig2.update_layout(
                xaxis_title='基質濃度 [mM]',
                yaxis_title='初速度 [Abs/s]',
                title='ミカエリス・メンテンプロット'
            )
            st.plotly_chart(fig2, use_container_width=True)

            def michaelis_menten(S, Vmax, Km):
                return (Vmax * S) / (Km + S)

            popt, _ = curve_fit(michaelis_menten, substrate_concs, velocities, maxfev=10000)
            Vmax, Km = popt
            st.success(f"Vmax = {Vmax:.4f} Abs/s, Km = {Km:.4f} mM")
else:
    st.warning("Excelファイルをアップロードしてください。")
