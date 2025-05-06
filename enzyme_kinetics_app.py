import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(layout="wide")
st.title("🧬 酵素キネティクス解析ツール")

# ファイルアップロード
uploaded_file = st.sidebar.file_uploader("ExcelまたはCSVファイルをアップロード", type=["csv", "xlsx"])
substrate_concentration = st.sidebar.text_input("基質濃度（カンマ区切りで入力）", "1, 2, 5, 10, 20")

# グラフ用の範囲指定
time_range = st.sidebar.slider("表示する時間範囲（秒）", 0, 1000, (0, 300))

def michaelis_menten(S, Vmax, Km):
    return (Vmax * S) / (Km + S)

if uploaded_file:
    # データ読み込み
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error(f"ファイルの読み込みに失敗しました: {e}")
        st.stop()

    # 時間データと吸光度データの抽出
    try:
        df = df.dropna(how="all")
        data_start = df[df.iloc[:, 0].astype(str).str.contains("XYDATA", na=False)].index[0] + 1
        df_data = df.iloc[data_start:].reset_index(drop=True)
        df_data.columns = ["Time", "Sample", "Wavelength", *[f"Sample {i}" for i in range(1, len(df.columns) - 3 + 1)]]

        time = pd.to_numeric(df_data["Time"], errors="coerce")
        df_numeric = df_data.drop(columns=["Time", "Sample", "Wavelength"])
        df_numeric = df_numeric.apply(pd.to_numeric, errors="coerce")

        # 時間範囲のフィルタ
        mask = (time >= time_range[0]) & (time <= time_range[1])
        time_filtered = time[mask]
        df_filtered = df_numeric[mask]

        # Plotlyによるインタラクティブグラフ
        fig = go.Figure()
        for col in df_filtered.columns:
            fig.add_trace(go.Scatter(x=time_filtered, y=df_filtered[col],
                                     mode='lines+markers',
                                     name=col,
                                     hovertemplate='時間: %{x} 秒<br>吸光度: %{y}<extra></extra>'))

        fig.update_layout(title="時間 vs 吸光度（拡大・範囲選択可能）",
                          xaxis_title="時間（秒）",
                          yaxis_title="吸光度",
                          hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

        # 初速度計算とMMプロット
        st.header("📈 初速度とミカエリス・メンテンフィット")

        try:
            concs = list(map(float, substrate_concentration.split(',')))
            initial_rates = []

            for col in df_filtered.columns:
                y = df_filtered[col].values
                x = time_filtered.values
                # 初期5点で直線フィッティング
                slope, _ = np.polyfit(x[:5], y[:5], 1)
                initial_rates.append(slope)

            popt, _ = curve_fit(michaelis_menten, concs, initial_rates)
            Vmax, Km = popt

            fig_mm = go.Figure()
            fig_mm.add_trace(go.Scatter(x=concs, y=initial_rates,
                                        mode='markers',
                                        name='初速度'))
            S_range = np.linspace(min(concs), max(concs), 100)
            fig_mm.add_trace(go.Scatter(x=S_range, y=michaelis_menten(S_range, *popt),
                                        mode='lines',
                                        name='MMフィット'))

            fig_mm.update_layout(title=f"ミカエリス・メンテンプロット (Vmax={Vmax:.3f}, Km={Km:.3f})",
                                 xaxis_title="基質濃度",
                                 yaxis_title="初速度")
            st.plotly_chart(fig_mm, use_container_width=True)

        except Exception as e:
            st.warning(f"初速度やフィッティング処理に問題がありました: {e}")

    except Exception as e:
        st.error(f"データ解析に失敗しました: {e}")
