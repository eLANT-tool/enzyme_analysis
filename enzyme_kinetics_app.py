import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO
from scipy.optimize import curve_fit

st.set_page_config(page_title="酵素キネティクス解析ツール", layout="wide")

# ヘルプ表示
with st.expander("❓ ヘルプ・使い方はこちら"):
    st.markdown("""
    ### 📘 使用方法
    - **Excelファイルの形式**：以下のような形式でデータを準備してください。
        - A列：時間（秒）
        - B列：測定番号
        - C列：吸光度（ラベル）
        - D列以降：各サンプルの吸光度データ
    - **範囲選択**：グラフを拡大して範囲を指定できます（範囲選択は下記対応予定）。
    - **濃度入力**：測定ごとの基質濃度を手動で入力してください。

    ### ⚠️ よくあるエラー
    - ファイル形式が `.xlsx` または `.csv` でない
    - A列に時間（数値）がない
    - データが途中で空欄や文字列になっている

    ### 💡 サンプルデータのダウンロード
    下のボタンからテスト用のExcelデータをダウンロードできます。
    """)

    # サンプルデータ作成
    sample_df = pd.DataFrame({
        "Time (s)": np.arange(0, 300, 10),
        "Sample1": np.linspace(0.05, 0.8, 30) + np.random.normal(0, 0.02, 30),
        "Sample2": np.linspace(0.05, 0.6, 30) + np.random.normal(0, 0.02, 30)
    })
    output = BytesIO()
    sample_df.to_excel(output, index=False)
    st.download_button("📥 サンプルExcelをダウンロード", data=output.getvalue(), file_name="sample_data.xlsx")

# ファイルアップロード
st.sidebar.header("1. データファイルのアップロード")
uploaded_file = st.sidebar.file_uploader("ExcelまたはCSVファイルをアップロード", type=["xlsx", "csv"])

if uploaded_file is not None:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.success("ファイルを読み込みました！")
    st.dataframe(df.head())

    # 時間列検出
    time_col = df.columns[0]
    time = df[time_col].values

    # 濃度入力
    st.sidebar.header("2. 基質濃度の入力")
    substrate_concs = []
    num_samples = len(df.columns) - 1
    for i in range(1, len(df.columns)):
        col_name = df.columns[i]
        conc = st.sidebar.number_input(f"{col_name} の濃度 [mM]", min_value=0.0, value=1.0, step=0.1)
        substrate_concs.append(conc)

    # グラフ描画
    st.subheader("🧪 吸光度 vs 時間 グラフ")
    fig, ax = plt.subplots()
    for i in range(1, len(df.columns)):
        ax.plot(time, df.iloc[:, i], label=df.columns[i])
    ax.set_xlabel("時間 (秒)")
    ax.set_ylabel("吸光度")
    ax.legend()
    st.pyplot(fig)

    # 初速度の計算
    st.subheader("🚀 初速度の自動計算（単純近似）")
    initial_rates = []
    for i in range(1, len(df.columns)):
        y = df.iloc[:, i].values
        slope, _ = np.polyfit(time[:5], y[:5], 1)
        initial_rates.append(slope)
    st.write("初速度一覧：", dict(zip(df.columns[1:], initial_rates)))

    # ミカエリス・メンテンフィッティング
    def michaelis_menten(S, Vmax, Km):
        return (Vmax * S) / (Km + S)

    try:
        popt, _ = curve_fit(michaelis_menten, substrate_concs, initial_rates)
        Vmax, Km = popt
        st.subheader("📈 ミカエリス・メンテンプロット")
        S_fit = np.linspace(min(substrate_concs), max(substrate_concs), 100)
        v_fit = michaelis_menten(S_fit, Vmax, Km)

        fig2, ax2 = plt.subplots()
        ax2.scatter(substrate_concs, initial_rates, label="実測")
        ax2.plot(S_fit, v_fit, label=f"フィット: Vmax={Vmax:.2f}, Km={Km:.2f}", color="red")
        ax2.set_xlabel("基質濃度 [mM]")
        ax2.set_ylabel("初速度")
        ax2.legend()
        st.pyplot(fig2)
    except Exception as e:
        st.error(f"ミカエリス・メンテンフィッティングに失敗しました: {e}")
else:
    st.info("左のサイドバーからExcelまたはCSVファイルをアップロードしてください。")
