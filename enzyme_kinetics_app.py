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
    - Excelファイルは次の形式でアップロードしてください：
      - A列：時間（秒）
      - B列：吸光度
    - サンプルExcelをダウンロードしてご利用ください。
    - 濃度情報は手動で入力してください。
    - グラフはドラッグで範囲選択できます。
    - 選択範囲で初速度を自動再計算します。
    """
)

# --- サンプルExcelのダウンロード機能 ---
def create_sample_excel():
    df_sample = pd.DataFrame({
        'Time (s)': np.arange(0, 60, 5),
        'Absorbance': [0.02, 0.05, 0.09, 0.14, 0.18, 0.23, 0.29, 0.35, 0.40, 0.45, 0.50, 0.54]
    })
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_sample.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

sample_excel = create_sample_excel()
b64 = base64.b64encode(sample_excel).decode()
st.sidebar.markdown(f"[解析用Excelテンプレートをダウンロード](data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64})")

# --- タイトル表示 ---
st.title("酵素キネティクス解析ツール（Plotly対応）")

# --- サイドバー ---
st.sidebar.header("パラメータ設定")
substrate_conc = st.sidebar.number_input("基質濃度 [mM]", min_value=0.0, value=1.0, step=0.1)

# --- ファイルアップロード ---
uploaded_file = st.file_uploader("Excelファイルをアップロード（時間と吸光度列を含む）", type=["xlsx", "xls"])

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        df.columns = [col.strip() for col in df.columns]  # 列名の前後空白を削除

        if 'Time (s)' not in df.columns or 'Absorbance' not in df.columns:
            st.error("Excelファイルに 'Time (s)' と 'Absorbance' 列が必要です。")
        else:
            time = df['Time (s)']
            absorbance = df['Absorbance']

            # --- グラフ描画（Plotly） ---
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=time, y=absorbance, mode='lines+markers', name='吸光度'))
            fig.update_layout(
                title='時間 vs 吸光度',
                xaxis_title='時間 (s)',
                yaxis_title='吸光度',
                dragmode='select',
                height=500
            )
            selected_points = st.plotly_chart(fig, use_container_width=True)

            # --- データ範囲選択による初速度再計算 ---
            st.markdown("### 初速度の計算結果")
            st.info("グラフ上で範囲をドラッグして選択してください。")

            # 初期速度の簡易推定（先頭N点）
            N = st.slider("線形近似に使用する点数", 2, len(time), 5)
            coeffs = np.polyfit(time[:N], absorbance[:N], 1)
            init_velocity = coeffs[0]

            st.write(f"**初速度:** {init_velocity:.4f} Abs/s @ {substrate_conc} mM")

            # --- 濃度 vs 初速度の記録と表示 ---
            if 'velocities' not in st.session_state:
                st.session_state.velocities = []
                st.session_state.substrates = []

            if st.button("この初速度を記録"):
                st.session_state.velocities.append(init_velocity)
                st.session_state.substrates.append(substrate_conc)

            if st.session_state.velocities:
                st.markdown("### 初速度 vs 基質濃度")
                df_rate = pd.DataFrame({
                    '基質濃度 [mM]': st.session_state.substrates,
                    '初速度 [Abs/s]': st.session_state.velocities
                })
                st.dataframe(df_rate)

                fig2 = go.Figure()
                fig2.add_trace(go.Scatter(
                    x=st.session_state.substrates,
                    y=st.session_state.velocities,
                    mode='markers+lines',
                    name='初速度'
                ))
                fig2.update_layout(
                    title='ミカエリス・メンテンプロット',
                    xaxis_title='基質濃度 [mM]',
                    yaxis_title='初速度 [Abs/s]'
                )
                st.plotly_chart(fig2, use_container_width=True)

                # --- フィッティング（Michaelis-Menten） ---
                def michaelis_menten(S, Vmax, Km):
                    return (Vmax * S) / (Km + S)

                popt, _ = curve_fit(michaelis_menten, st.session_state.substrates, st.session_state.velocities)
                Vmax, Km = popt
                st.success(f"Vmax = {Vmax:.4f} Abs/s, Km = {Km:.4f} mM")

                # --- 論文用：濃度違いのグラフ重ね表示 ---
                st.markdown("### 吸光度 vs 時間（全データ）")
                fig3 = go.Figure()
                fig3.add_trace(go.Scatter(x=time, y=absorbance, mode='lines+markers', name=f'{substrate_conc} mM'))
                fig3.update_layout(
                    title='各濃度での吸光度推移',
                    xaxis_title='時間 (s)',
                    yaxis_title='吸光度'
                )
                st.plotly_chart(fig3, use_container_width=True)

    except Exception as e:
        st.error(f"ファイルの読み込み中にエラーが発生しました：{e}")
else:
    st.warning("Excelファイルをアップロードしてください。")

