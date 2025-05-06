import os
import sys

if getattr(sys, 'frozen', False):
    # アプリケーションが凍結されている場合（exeファイルとして実行されている場合）
    bundle_dir = sys._MEIPASS
else:
    # 通常のPythonスクリプトとして実行されている場合
    bundle_dir = os.path.dirname(os.path.abspath(__file__))

# Streamlitの設定ファイルのパスを指定
os.environ['STREAMLIT_CONFIG_DIR'] = os.path.join(bundle_dir, 'streamlit')

# 以下、元のコード
import streamlit as st
# ... (残りのコード)

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
import io
import base64
from matplotlib.figure import Figure
import matplotlib
matplotlib.use('Agg')  # バックエンドを設定

# アプリのスタイル設定
st.set_page_config(
    page_title="酵素キネティクス計算ツール",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# カスタムCSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #0D47A1;
        margin-top: 2rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid #1E88E5;
        padding-bottom: 0.5rem;
    }
    .info-box {
        background-color: #E3F2FD;
        padding: 1rem;
        border-radius: 5px;
        border-left: 5px solid #1E88E5;
        margin-bottom: 1rem;
    }
    .result-box {
        background-color: #E8F5E9;
        padding: 1rem;
        border-radius: 5px;
        border-left: 5px solid #4CAF50;
        margin-bottom: 1rem;
    }
    .stButton button {
        background-color: #1E88E5;
        color: white;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Michaelis–Menten のモデル関数
def michaelis_menten(S, Vmax, Km):
    return (Vmax * S) / (Km + S)

# 時間-吸光度プロットを作成する関数
def plot_time_absorbance(df, time_col='Time', selected_columns=None):
    fig, ax = plt.subplots(figsize=(10, 6))
    
    if selected_columns is None:
        selected_columns = [col for col in df.columns if col != time_col]
    
    for col in selected_columns:
        if col != time_col and col in df.columns:
            ax.plot(df[time_col], df[col], 'o-', label=f"{col}")
    
    ax.set_xlabel('時間', fontsize=12)
    ax.set_ylabel('吸光度', fontsize=12)
    ax.grid(True, linestyle='--', alpha=0.7)
    ax.legend(fontsize=10)
    ax.set_title('時間-吸光度プロット', fontsize=14)
    plt.tight_layout()
    return fig

# 初速度を線形回帰（最初のn_points）で求める関数
def calculate_initial_velocity(time, absorbance, n_points):
    if n_points > len(time):
        n_points = len(time)
    
    coeff = np.polyfit(time[:n_points], absorbance[:n_points], 1)
    slope = coeff[0]
    intercept = coeff[1]
    
    # 線形回帰の結果をプロットするためのデータを返す
    x_fit = np.linspace(min(time[:n_points]), max(time[:n_points]), 100)
    y_fit = slope * x_fit + intercept
    
    return slope, x_fit, y_fit

# 初速度計算のプロットを作成する関数
def plot_initial_velocity(time, absorbance, n_points, substrate_conc):
    slope, x_fit, y_fit = calculate_initial_velocity(time, absorbance, n_points)
    
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.scatter(time[:n_points], absorbance[:n_points], color='blue', label='使用データ')
    ax.scatter(time[n_points:], absorbance[n_points:], color='lightgray', label='未使用データ')
    ax.plot(x_fit, y_fit, 'r-', label=f'傾き = {slope:.4f}')
    
    ax.set_xlabel('時間', fontsize=12)
    ax.set_ylabel('吸光度', fontsize=12)
    ax.set_title(f'基質濃度 {substrate_conc} - 初速度計算', fontsize=14)
    ax.grid(True, linestyle='--', alpha=0.7)
    ax.legend(fontsize=10)
    plt.tight_layout()
    
    return fig, slope

# Michaelis–Menten プロットを作成する関数
def plot_michaelis_menten(S, v, Vmax, Km):
    S_fit = np.linspace(0, max(S) * 1.2, 100)
    v_fit = michaelis_menten(S_fit, Vmax, Km)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(S, v, color='blue', s=80, label='実験データ')
    ax.plot(S_fit, v_fit, 'r-', linewidth=2, label=f'Michaelis-Menten フィット\nVmax = {Vmax:.4f}\nKm = {Km:.4f}')
    
    ax.set_xlabel('基質濃度', fontsize=12)
    ax.set_ylabel('初速度', fontsize=12)
    ax.set_title('Michaelis-Menten プロット', fontsize=14)
    ax.grid(True, linestyle='--', alpha=0.7)
    ax.legend(fontsize=10)
    plt.tight_layout()
    
    return fig

# Lineweaver–Burk プロットを作成する関数
def plot_lineweaver_burk(S, v):
    # 0除算を避けるために numpy 配列に変換
    S = np.array(S, dtype=float)
    v = np.array(v, dtype=float)
    inv_S = 1.0 / S
    inv_v = 1.0 / v
    
    # 直線フィッティング (inv_v = (Km/Vmax)*(1/S) + (1/Vmax))
    coeff = np.polyfit(inv_S, inv_v, 1)
    slope = coeff[0]  # Km/Vmax
    intercept = coeff[1]  # 1/Vmax
    
    Vmax_lb = 1.0 / intercept
    Km_lb = slope * Vmax_lb
    
    x_fit = np.linspace(min(inv_S) * 0.8, max(inv_S) * 1.2, 100)
    y_fit = np.polyval(coeff, x_fit)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(inv_S, inv_v, color='blue', s=80, label='実験データ')
    ax.plot(x_fit, y_fit, 'r-', linewidth=2, 
            label=f'Lineweaver-Burk フィット\nVmax = {Vmax_lb:.4f}\nKm = {Km_lb:.4f}')
    
    # x軸とy軸の交点を表示
    ax.axhline(y=0, color='black', linestyle='-', alpha=0.3)
    ax.axvline(x=0, color='black', linestyle='-', alpha=0.3)
    
    # -1/Km の位置に垂直線
    x_intercept = -1.0 / Km_lb
    ax.axvline(x=x_intercept, color='green', linestyle='--', alpha=0.5, 
               label=f'x切片 = {x_intercept:.4f} (-1/Km)')
    
    ax.set_xlabel('1/基質濃度', fontsize=12)
    ax.set_ylabel('1/初速度', fontsize=12)
    ax.set_title('Lineweaver-Burk プロット', fontsize=14)
    ax.grid(True, linestyle='--', alpha=0.7)
    ax.legend(fontsize=10)
    plt.tight_layout()
    
    return fig, Vmax_lb, Km_lb

# Eadie-Hofstee プロットを作成する関数
def plot_eadie_hofstee(S, v):
    S = np.array(S, dtype=float)
    v = np.array(v, dtype=float)
    v_S = v / S
    
    # 直線フィッティング (v = -Km*(v/S) + Vmax)
    coeff = np.polyfit(v_S, v, 1)
    slope = coeff[0]  # -Km
    intercept = coeff[1]  # Vmax
    
    Vmax_eh = intercept
    Km_eh = -slope
    
    x_fit = np.linspace(min(v_S) * 0.8, max(v_S) * 1.2, 100)
    y_fit = np.polyval(coeff, x_fit)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(v_S, v, color='blue', s=80, label='実験データ')
    ax.plot(x_fit, y_fit, 'r-', linewidth=2, 
            label=f'Eadie-Hofstee フィット\nVmax = {Vmax_eh:.4f}\nKm = {Km_eh:.4f}')
    
    ax.set_xlabel('v/[S]', fontsize=12)
    ax.set_ylabel('v', fontsize=12)
    ax.set_title('Eadie-Hofstee プロット', fontsize=14)
    ax.grid(True, linestyle='--', alpha=0.7)
    ax.legend(fontsize=10)
    plt.tight_layout()
    
    return fig, Vmax_eh, Km_eh

# Hanes-Woolf プロットを作成する関数
def plot_hanes_woolf(S, v):
    S = np.array(S, dtype=float)
    v = np.array(v, dtype=float)
    S_v = S / v
    
    # 直線フィッティング (S/v = (1/Vmax)*S + Km/Vmax)
    coeff = np.polyfit(S, S_v, 1)
    slope = coeff[0]  # 1/Vmax
    intercept = coeff[1]  # Km/Vmax
    
    Vmax_hw = 1.0 / slope
    Km_hw = intercept * Vmax_hw
    
    x_fit = np.linspace(min(S) * 0.8, max(S) * 1.2, 100)
    y_fit = np.polyval(coeff, x_fit)
    
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.scatter(S, S_v, color='blue', s=80, label='実験データ')
    ax.plot(x_fit, y_fit, 'r-', linewidth=2, 
            label=f'Hanes-Woolf フィット\nVmax = {Vmax_hw:.4f}\nKm = {Km_hw:.4f}')
    
    ax.set_xlabel('[S]', fontsize=12)
    ax.set_ylabel('[S]/v', fontsize=12)
    ax.set_title('Hanes-Woolf プロット', fontsize=14)
    ax.grid(True, linestyle='--', alpha=0.7)
    ax.legend(fontsize=10)
    plt.tight_layout()
    
    return fig, Vmax_hw, Km_hw

# グラフをダウンロードするための関数
def get_image_download_link(fig, filename, text):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=300)
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode()
    href = f'<a href="data:image/png;base64,{b64}" download="{filename}.png">{text}</a>'
    return href

# データをCSVとしてダウンロードするための関数
def get_csv_download_link(df, filename, text):
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}.csv">{text}</a>'
    return href

# サンプルデータを生成する関数
def generate_sample_data():
    # 基質濃度
    substrate_concs = [0.5, 1.0, 2.0, 5.0, 10.0, 20.0]
    
    # 時間ポイント
    time_points = np.linspace(0, 10, 11)
    
    # Michaelis-Menten パラメータ
    Vmax_true = 0.5
    Km_true = 2.0
    
    # データフレームを初期化
    df = pd.DataFrame({'Time': time_points})
    
    # 各基質濃度に対して時間-吸光度データを生成
    for conc in substrate_concs:
        # 初速度を計算
        v0 = michaelis_menten(conc, Vmax_true, Km_true)
        
        # ノイズを含む吸光度データを生成
        absorbance = v0 * time_points + 0.01 * np.random.randn(len(time_points))
        absorbance[0] = 0  # 初期値は0
        
        # データフレームに追加
        df[str(conc)] = absorbance
    
    return df

# Streamlit を用いたメイン処理
def main():
    st.markdown('<h1 class="main-header">🧪 酵素キネティクス計算ツール</h1>', unsafe_allow_html=True)
    
    st.markdown('<div class="info-box">このツールは酵素活性測定の計算とグラフ作成を支援します。時間-吸光度データから初速度を計算し、Michaelis-Menten パラメータを求めます。</div>', unsafe_allow_html=True)
    
    # サイドバー
    with st.sidebar:
        st.header("設定")
        
        # データ入力方法の選択
        data_input_method = st.radio(
            "データ入力方法を選択してください:",
            ["Excelファイルをアップロード", "サンプルデータを使用"]
        )
        
        # パラメータ設定
        st.subheader("パラメータ設定")
        time_col = st.text_input("時間のカラム名", value="Time")
        n_points = st.slider("初速度計算に使用するデータポイント数", min_value=2, max_value=20, value=5)
        enzyme_conc = st.number_input("酵素濃度 (μM)", value=1.0, step=0.1, format="%.3f")
        
        # 単位設定
        st.subheader("単位設定")
        time_unit = st.selectbox("時間の単位", ["秒", "分", "時間"], index=1)
        conc_unit = st.selectbox("濃度の単位", ["nM", "μM", "mM", "M"], index=1)
        
        # 表示設定
        st.subheader("表示設定")
        show_all_plots = st.checkbox("すべての変換プロットを表示", value=True)
        
        # ヘルプ情報
        st.markdown("---")
        st.markdown("### ヘルプ")
        with st.expander("使い方"):
            st.markdown("""
            1. Excelファイルをアップロードするか、サンプルデータを使用します
            2. 時間カラム名とパラメータを設定します
            3. 初速度計算に使用するデータポイント数を調整します
            4. 結果を確認し、必要に応じてグラフをダウンロードします
            """)
        
        with st.expander("データ形式について"):
            st.markdown("""
            Excelファイルは以下の形式である必要があります:
            - 最初の列が時間データ (例: 'Time')
            - それ以降の各列が基質濃度に対応する吸光度データ
            - 列名は基質濃度の数値である必要があります (例: '0.5', '1.0', '2.0')
            """)
    
    # メインコンテンツ
    if data_input_method == "Excelファイルをアップロード":
        uploaded_file = st.file_uploader("Excel ファイルを選択", type=["xlsx", "xls"])
        
        if uploaded_file is not None:
            try:
                # Excel ファイルの読み込み
                df = pd.read_excel(uploaded_file)
                process_data(df, time_col, n_points, enzyme_conc, time_unit, conc_unit, show_all_plots)
            except Exception as e:
                st.error(f"ファイルの読み込みに失敗しました。エラー: {str(e)}")
    else:
        # サンプルデータを使用
        if st.button("サンプルデータを生成"):
            df = generate_sample_data()
            process_data(df, time_col, n_points, enzyme_conc, time_unit, conc_unit, show_all_plots)

def process_data(df, time_col, n_points, enzyme_conc, time_unit, conc_unit, show_all_plots):
    st.markdown('<h2 class="sub-header">データプレビュー</h2>', unsafe_allow_html=True)
    st.dataframe(df.head())
    
    # データのダウンロードリンク
    st.markdown(get_csv_download_link(df, "enzyme_kinetics_data", "📥 データをCSVでダウンロード"), unsafe_allow_html=True)
    
    if time_col not in df.columns:
        st.error(f"指定された時間カラム名 '{time_col}' がデータに存在しません。")
        return
    
    # 時間-吸光度プロットの表示
    st.markdown('<h2 class="sub-header">時間-吸光度プロット</h2>', unsafe_allow_html=True)
    
    # 表示するカラムを選択
    data_columns = [col for col in df.columns if col != time_col]
    selected_columns = st.multiselect(
        "表示するデータ系列を選択",
        options=data_columns,
        default=data_columns
    )
    
    if selected_columns:
        fig_time = plot_time_absorbance(df, time_col, selected_columns)
        st.pyplot(fig_time)
        st.markdown(get_image_download_link(fig_time, "time_absorbance_plot", "📥 このグラフをダウンロード"), unsafe_allow_html=True)
    
    # 各条件ごとの初速度計算（カラム名が基質濃度と仮定）
    substrate_concentrations = []
    initial_velocities = []
    
    st.markdown('<h2 class="sub-header">各基質濃度での初速度</h2>', unsafe_allow_html=True)
    
    # 初速度計算結果を格納するデータフレーム
    velocity_data = {"基質濃度": [], "初速度": []}
    
    # 2列レイアウトで初速度計算結果を表示
    cols = st.columns(2)
    col_idx = 0
    
    for col in df.columns:
        if col == time_col:
            continue
        
        try:
            # カラム名を数値に変換できる場合、基質濃度として扱う
            S = float(col)
        except ValueError:
            st.warning(f"カラム '{col}' は基質濃度として解釈できないためスキップします。")
            continue
        
        time_data = df[time_col].to_numpy()
        absorbance_data = df[col].to_numpy()
        
        # 初速度計算とプロット
        with cols[col_idx % 2]:
            st.markdown(f"##### 基質濃度: {S} {conc_unit}")
            fig_velocity, slope = plot_initial_velocity(time_data, absorbance_data, n_points, S)
            st.pyplot(fig_velocity)
            st.markdown(f"初速度 = **{slope:.4f}** / {time_unit}")
            st.markdown(get_image_download_link(fig_velocity, f"velocity_plot_{S}", "📥 このグラフをダウンロード"), unsafe_allow_html=True)
        
        col_idx += 1
        
        substrate_concentrations.append(S)
        initial_velocities.append(slope)
        
        # データフレームに追加
        velocity_data["基質濃度"].append(S)
        velocity_data["初速度"].append(slope)
    
    if len(substrate_concentrations) == 0:
        st.error("基質濃度として変換可能なカラムが見つかりません。カラム名が数値であることを確認してください。")
        return
    
    # 初速度データの表示
    st.markdown('<h2 class="sub-header">初速度データ一覧</h2>', unsafe_allow_html=True)
    velocity_df = pd.DataFrame(velocity_data)
    st.dataframe(velocity_df)
    
    # 初速度データのダウンロードリンク
    st.markdown(get_csv_download_link(velocity_df, "initial_velocity_data", "📥 初速度データをCSVでダウンロード"), unsafe_allow_html=True)
    
    # Michaelis–Menten フィッティング
    try:
        st.markdown('<h2 class="sub-header">酵素キネティクスパラメータ</h2>', unsafe_allow_html=True)
        
        # 非線形フィッティング (Michaelis-Menten)
        popt, _ = curve_fit(michaelis_menten, substrate_concentrations, initial_velocities, bounds=(0, np.inf))
        Vmax, Km = popt
        
        # Lineweaver-Burk プロット
        fig_lb, Vmax_lb, Km_lb = plot_lineweaver_burk(substrate_concentrations, initial_velocities)
        
        # 追加のプロット
        if show_all_plots:
            # Eadie-Hofstee プロット
            fig_eh, Vmax_eh, Km_eh = plot_eadie_hofstee(substrate_concentrations, initial_velocities)
            
            # Hanes-Woolf プロット
            fig_hw, Vmax_hw, Km_hw = plot_hanes_woolf(substrate_concentrations, initial_velocities)
        
        # 結果の表示
        st.markdown('<div class="result-box">', unsafe_allow_html=True)
        
        # 3列レイアウトでパラメータを表示
        param_cols = st.columns(3)
        
        with param_cols[0]:
            st.markdown("#### Michaelis-Menten フィット")
            st.markdown(f"Vmax: **{Vmax:.4f}** / {time_unit}")
            st.markdown(f"Km: **{Km:.4f}** {conc_unit}")
            
            # Kcat の計算（酵素濃度で正規化）
            Kcat = Vmax / enzyme_conc
            st.markdown(f"Kcat: **{Kcat:.4f}** / {time_unit}")
            st.markdown(f"触媒効率 (Kcat/Km): **{Kcat/Km:.4f}** / ({time_unit}・{conc_unit})")
        
        with param_cols[1]:
            st.markdown("#### Lineweaver-Burk フィット")
            st.markdown(f"Vmax: **{Vmax_lb:.4f}** / {time_unit}")
            st.markdown(f"Km: **{Km_lb:.4f}** {conc_unit}")
            
            # Kcat の計算（酵素濃度で正規化）
            Kcat_lb = Vmax_lb / enzyme_conc
            st.markdown(f"Kcat: **{Kcat_lb:.4f}** / {time_unit}")
            st.markdown(f"触媒効率 (Kcat/Km): **{Kcat_lb/Km_lb:.4f}** / ({time_unit}・{conc_unit})")
        
        if show_all_plots:
            with param_cols[2]:
                st.markdown("#### 平均値")
                Vmax_avg = np.mean([Vmax, Vmax_lb, Vmax_eh, Vmax_hw])
                Km_avg = np.mean([Km, Km_lb, Km_eh, Km_hw])
                Kcat_avg = Vmax_avg / enzyme_conc
                
                st.markdown(f"Vmax: **{Vmax_avg:.4f}** / {time_unit}")
                st.markdown(f"Km: **{Km_avg:.4f}** {conc_unit}")
                st.markdown(f"Kcat: **{Kcat_avg:.4f}** / {time_unit}")
                st.markdown(f"触媒効率 (Kcat/Km): **{Kcat_avg/Km_avg:.4f}** / ({time_unit}・{conc_unit})")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Michaelis–Menten プロットの表示
        st.markdown('<h2 class="sub-header">Michaelis-Menten プロット</h2>', unsafe_allow_html=True)
        fig_mm = plot_michaelis_menten(substrate_concentrations, initial_velocities, Vmax, Km)
        st.pyplot(fig_mm)
        st.markdown(get_image_download_link(fig_mm, "michaelis_menten_plot", "📥 このグラフをダウンロード"), unsafe_allow_html=True)
        
        # Lineweaver–Burk プロットの表示
        st.markdown('<h2 class="sub-header">Lineweaver-Burk プロット</h2>', unsafe_allow_html=True)
        st.pyplot(fig_lb)
        st.markdown(get_image_download_link(fig_lb, "lineweaver_burk_plot", "📥 このグラフをダウンロード"), unsafe_allow_html=True)
        
        # 追加のプロットを表示
        if show_all_plots:
            # Eadie-Hofstee プロットの表示
            st.markdown('<h2 class="sub-header">Eadie-Hofstee プロット</h2>', unsafe_allow_html=True)
            st.pyplot(fig_eh)
            st.markdown(get_image_download_link(fig_eh, "eadie_hofstee_plot", "📥 このグラフをダウンロード"), unsafe_allow_html=True)
            
            # Hanes-Woolf プロットの表示
            st.markdown('<h2 class="sub-header">Hanes-Woolf プロット</h2>', unsafe_allow_html=True)
            st.pyplot(fig_hw)
            st.markdown(get_image_download_link(fig_hw, "hanes_woolf_plot", "📥 このグラフをダウンロード"), unsafe_allow_html=True)
        
    except Exception as e:
        st.error(f"酵素キネティクスパラメータの計算に失敗しました。エラー: {str(e)}")

if __name__ == '__main__':
    main()