"""
AI 台股當沖分析系統 - 主程式（整合資料庫快取 + 美化版）
"""

import streamlit as st
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()
FINMIND_TOKEN = os.getenv("FINMIND_TOKEN")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")

# ✅ 新增：支援 Streamlit Cloud secrets
def get_api_key(key_name):
    """獲取 API 金鑰（支援本地 .env 和 Streamlit Cloud secrets）"""
    # 優先使用 Streamlit secrets
    if hasattr(st, 'secrets') and key_name in st.secrets:
        return st.secrets[key_name]
    # 其次使用環境變數
    return os.getenv(key_name)

# 設定 API 金鑰
os.environ['PERPLEXITY_API_KEY'] = get_api_key('PERPLEXITY_API_KEY') or ''
os.environ['FINMIND_API_KEY'] = get_api_key('FINMIND_API_KEY') or ''

# 檢查必要的 API 金鑰
if not os.environ.get('PERPLEXITY_API_KEY'):
    st.error("❌ 未設定 APERPLEXITY_API_KEY")
    st.info("請在 Streamlit Cloud 的 Settings → Secrets 中設定 API 金鑰")
    st.stop()
    
# 導入自定義模組
from modules.data_fetcher import get_stock_data, get_stock_name
from modules.technical_indicators import (
    calculate_technical_indicators, 
    calculate_support_resistance,
    calculate_stop_loss_take_profit,
    get_daytrading_signals
)
from modules.chart_plotter import plot_candlestick_chart, get_signal_summary
from modules.ai_analyzer import search_news_events, generate_daytrading_analysis
from modules.utils import validate_inputs, format_currency, calculate_position_size
from modules.database import get_database


# 頁面配置
st.set_page_config(
    page_title="AI 台股當沖分析系統",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🎨 自定義 CSS 樣式
st.markdown("""
<style>
    /* 淡紫色按鈕樣式 */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 12px 24px;
        font-weight: 600;
        font-size: 16px;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
        transform: translateY(-2px);
    }
    
    /* 側邊欄樣式優化 */
    .css-1d391kg {
        background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%);
    }
    
    /* 指標卡片樣式 */
    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin: 10px 0;
    }
    
    /* 標題樣式 */
    h1 {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
    }
</style>
""", unsafe_allow_html=True)

# 初始化資料庫
@st.cache_resource
def init_database():
    """初始化資料庫連線"""
    return get_database()

db = init_database()

# 主標題
st.title("🎯 AI 台股當沖分析系統")
st.divider()

# 側邊欄 - 輸入控制區
with st.sidebar:
    st.header("⚙️ 當沖分析設定")
    st.divider()
    
    # API 測試按鈕
    if st.button("🧪 測試 FinMind API", use_container_width=True):
        with st.spinner("測試中..."):
            from modules.data_fetcher import test_finmind_api
            
            test_result = test_finmind_api(FINMIND_TOKEN, "2330")
            
            if test_result["success"]:
                st.success(f"✅ API 測試成功！")
                st.info(f"可用欄位: {', '.join(test_result['columns'])}")
                st.metric("數據筆數", test_result['data_count'])
            else:
                st.error(f"❌ API 測試失敗")
                st.error(f"錯誤訊息: {test_result['message']}")
    
    st.divider()
    
    # 股票代碼輸入
    stock_symbol = st.text_input(
        "📊 股票代碼",
        placeholder="例如: 2330, 2317, 0050",
        help="請輸入台股股票代碼（可含或不含 .TW）"
    )
    
    # 當日開盤價輸入（必填）
    today_open = st.number_input(
        "💰 當日開盤價 (必填)",
        min_value=0.0,
        step=0.1,
        format="%.2f",
        help="請輸入今日開盤價格,用於當沖決策判斷"
    )
    
    # 昨日收盤價輸入（選填）
    yesterday_close = st.number_input(
        "📅 昨日收盤價 (選填)",
        min_value=0.0,
        step=0.1,
        format="%.2f",
        value=0.0,
        help="若未填寫,系統將自動從歷史數據取得"
    )
    
    st.divider()
    
    # 🆕 開始當沖分析按鈕（移到這裡，淡紫色）
    analyze_button = st.button(
        "🚀 開始當沖分析", 
        use_container_width=True,
        type="primary"
    )
    
    st.divider()
    
    # API 金鑰輸入
    finmind_token = st.text_input(
        "🔑 FinMind API Token",
        type="password",
        value=FINMIND_TOKEN or "",
        help="請輸入您的 FinMind API Token"
    )
    
    perplexity_api_key = st.text_input(
        "🤖 Perplexity API Key",
        type="password",
        value=PERPLEXITY_API_KEY or "",
        help="請輸入您的 Perplexity API Key"
    )
    
    st.divider()
    
    # 分析參數設定
    analysis_days = st.slider(
        "📆 分析天數",
        min_value=30,
        max_value=90,
        value=60,
        help="選擇要分析的歷史數據天數"
    )
    
    st.divider()
    
    # 交易成本設定
    st.subheader("💸 交易成本設定")
    fee_discount = st.number_input(
        "手續費折扣 (折)",
        min_value=1.0,
        max_value=10.0,
        value=2.8,
        step=0.1,
        format="%.1f"
    )
    
    tax_rate = st.number_input(
        "證交稅率 (%)",
        min_value=0.0,
        max_value=1.0,
        value=0.15,
        step=0.01,
        format="%.2f"
    )
    
    st.divider()
    
    # 風險參數設定
    st.subheader("⚠️ 風險參數設定")
    total_capital = st.number_input(
        "總交易資金 (元)",
        min_value=10000,
        max_value=10000000,
        value=100000,
        step=10000,
        format="%d"
    )
    
    risk_percent = st.number_input(
        "單筆風險比例 (%)",
        min_value=0.1,
        max_value=5.0,
        value=1.0,
        step=0.1,
        format="%.1f"
    )
    
    st.divider()
    st.subheader("💾 資料庫設定")
    
    force_update = st.checkbox(
        "強制從 API 更新數據",
        value=False,
        help="勾選後將忽略快取,直接從 FinMind 和 Perplexity 獲取最新數據"
    )
    
    # 是否使用新聞分析
    use_news_analysis = st.checkbox(
        "啟用新聞分析 (消耗 Perplexity Token)",
        value=False,
        help="關閉後將僅使用 FinMind 技術數據進行分析，大幅節省 API 消耗"
    )
    
    show_stats = st.checkbox(
        "顯示查詢統計",
        value=False,
        help="顯示資料庫使用統計和 API 節省情況"
    )
    
    if st.button("🗑️ 清理舊數據 (90天前)", use_container_width=True, help="清理 90 天前的歷史數據以節省空間"):
        with st.spinner("清理中..."):
            db.cleanup_old_data(days=90)
            st.success("✅ 清理完成")
    
    # 免責聲明
    st.markdown("""
    ### 📢 免責聲明
    本系統僅供學術研究與教育用途,AI 提供的數據與分析結果僅供參考,**不構成投資建議或財務建議**。
    
    **當沖交易風險警告**:
    - 當沖交易屬於高風險投資行為
    - 可能導致本金全部損失
    - 交易成本與滑價會顯著影響獲利
    - 需要全程盯盤與快速決策能力
    - 不適合所有投資人
    
    請使用者自行判斷投資決策,並承擔相關風險。本系統作者不對任何投資行為負責,亦不承擔任何損失責任。
    
    歷史數據不代表未來結果。請務必做好風險控管,嚴格執行停損紀律。
    """)

# 🆕 主要執行邏輯（按鈕觸發）
if analyze_button:
    # 驗證輸入
    validation_result = validate_inputs(
        stock_symbol, 
        today_open, 
        finmind_token, 
        perplexity_api_key
    )
    
    if not validation_result["valid"]:
        st.error(validation_result["message"])
    else:
        # 處理股票代碼格式
        symbol = stock_symbol.strip().upper()
        if not symbol.endswith(".TW"):
            symbol = f"{symbol}.TW"
        
        # 取得股票代碼和中文名稱
        stock_code, stock_name = get_stock_name(symbol)
        
        # 建立顯示用名稱
        if stock_name and stock_name != stock_code:
            display_name = f"{stock_code} {stock_name}"
        else:
            display_name = stock_code
        
        # 顯示股票名稱
        st.info(f"📊 正在分析：**{display_name}**")
        
        # 記錄查詢
        db.log_query(symbol, 'analysis')
        
        # 顯示分析模式
        if use_news_analysis:
            st.info("🔍 分析模式：完整分析（技術面 + 籌碼面 + 新聞面）")
        else:
            st.info("⚡ 分析模式：快速分析（僅技術面 + 籌碼面，節省 Token）")
        
        # 計算日期範圍
        end_date = datetime.now()
        start_date = end_date - timedelta(days=analysis_days + 30)
        
        try:
            # 步驟1: 獲取股票數據
            with st.spinner(f"📊 正在獲取 {display_name} 的數據..."):
                stock_data = get_stock_data(
                    symbol,
                    start_date.strftime("%Y-%m-%d"),
                    end_date.strftime("%Y-%m-%d"),
                    finmind_token,
                    force_update=force_update
                )
                
                if stock_data is None or stock_data.empty:
                    st.error(f"❌ 無法獲取 {stock_code} 的數據,請檢查股票代碼或 API Token")
                    st.stop()
                
                st.success(f"✅ 成功獲取 {len(stock_data)} 筆交易數據")
            
            # 步驟2: 計算技術指標
            with st.spinner("🔢 計算技術指標..."):
                stock_data = calculate_technical_indicators(stock_data)
                st.success("✅ 技術指標計算完成")
            
            # 步驟3: 計算支撐壓力位
            with st.spinner("📍 計算支撐壓力位..."):
                support_resistance = calculate_support_resistance(stock_data)
                st.success("✅ 支撐壓力位計算完成")
            
            # 步驟4: 獲取籌碼數據
            with st.spinner("💼 獲取三大法人數據..."):
                try:
                    from modules.data_fetcher import get_institutional_data as fetch_institutional
                    
                    institutional_data = fetch_institutional(
                        symbol,
                        start_date.strftime("%Y-%m-%d"),
                        end_date.strftime("%Y-%m-%d"),
                        finmind_token,
                        force_update=force_update
                    )
                    
                    if institutional_data is not None and not institutional_data.empty:
                        st.success(f"✅ 成功獲取 {len(institutional_data)} 筆籌碼數據")
                    else:
                        st.warning("⚠️ 無法獲取籌碼數據,將繼續分析")
                        institutional_data = None
                except Exception as e:
                    st.warning(f"⚠️ 獲取籌碼數據時發生錯誤: {e}")
                    institutional_data = None
            
            # 步驟5: 搜尋新聞事件（條件式執行）
            news_result = None
            if use_news_analysis:
                with st.spinner(f"🔍 搜尋 {display_name} 的新聞事件..."):
                    news_result = search_news_events(
                        stock_code,
                        perplexity_api_key,
                        force_update=force_update
                    )
                    
                    if news_result and not news_result.get('is_fallback', False):
                        st.success("✅ 新聞事件搜尋完成")
                    else:
                        st.warning("⚠️ 新聞搜尋失敗,將使用備用方案")
            else:
                st.info("⏭️ 已跳過新聞分析（節省 Token 模式）")
            
            # 步驟6: 生成 AI 分析
            with st.spinner("🤖 生成 AI 當沖分析報告..."):
                # 使用最後一筆數據的收盤價作為昨日收盤價
                yesterday_close_value = float(stock_data.iloc[-1]['close'])
                
                ai_analysis = generate_daytrading_analysis(
                    symbol=stock_code,
                    stock_data=stock_data,
                    today_open=today_open,
                    yesterday_close=yesterday_close_value,
                    support_resistance=support_resistance,
                    institutional_data=institutional_data,
                    news_events=news_result,
                    api_key=perplexity_api_key,
                    fee_discount=fee_discount,
                    tax_rate=tax_rate,
                    total_capital=total_capital,
                    risk_percent=risk_percent
                )
                
                st.success("✅ AI 分析完成")
            
            # 顯示結果
            st.success("🎉 分析完成！")
            
            # 建立分頁（動態調整）
            if use_news_analysis:
                tab1, tab2, tab3, tab4, tab5 = st.tabs([
                    "📈 K線圖", 
                    "📊 技術指標", 
                    "💼 籌碼分析", 
                    "📰 新聞事件",
                    "🤖 AI 分析報告"
                ])
            else:
                tab1, tab2, tab3, tab5 = st.tabs([
                    "📈 K線圖", 
                    "📊 技術指標", 
                    "💼 籌碼分析", 
                    "🤖 AI 分析報告"
                ])
                tab4 = None
            
            # Tab 1: K線圖
            with tab1:
                st.subheader(f"📈 {display_name} K線圖與技術指標")
                
                # 繪製美化版圖表
                fig = plot_candlestick_chart(stock_data, stock_code, stock_name)
                st.plotly_chart(fig, use_container_width=True)
                
                # 顯示技術訊號摘要
                st.divider()
                st.subheader("📊 技術訊號摘要")
                
                signal_summary = get_signal_summary(stock_data)
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.markdown("### 均線訊號")
                    if signal_summary['ma_golden_cross']:
                        recent_golden = signal_summary['ma_golden_cross'][-1]
                        st.success(f"🟢 黃金交叉")
                        st.caption(f"最近: {recent_golden[0].strftime('%Y-%m-%d')}")
                        st.caption(f"價格: NT$ {recent_golden[1]:.2f}")
                    elif signal_summary['ma_death_cross']:
                        recent_death = signal_summary['ma_death_cross'][-1]
                        st.error(f"🔴 死亡交叉")
                        st.caption(f"最近: {recent_death[0].strftime('%Y-%m-%d')}")
                        st.caption(f"價格: NT$ {recent_death[1]:.2f}")
                    else:
                        st.info("⚪ 無明顯訊號")
                
                with col2:
                    st.markdown("### RSI 狀態")
                    if signal_summary['rsi_overbought']:
                        st.warning("⚠️ RSI 超買 (>70)")
                        st.caption("建議: 注意回檔風險")
                    elif signal_summary['rsi_oversold']:
                        st.info("💡 RSI 超賣 (<30)")
                        st.caption("建議: 可能反彈機會")
                    else:
                        st.success("✅ RSI 正常")
                        st.caption("區間: 30-70")
                
                with col3:
                    st.markdown("### KD 狀態")
                    if signal_summary['kd_overbought']:
                        st.warning("⚠️ KD 超買 (>80)")
                        st.caption("建議: 短線過熱")
                    elif signal_summary['kd_oversold']:
                        st.info("💡 KD 超賣 (<20)")
                        st.caption("建議: 短線超跌")
                    else:
                        st.success("✅ KD 正常")
                        st.caption("區間: 20-80")
                    
                    # KD 交叉訊號
                    if signal_summary['kd_golden_cross']:
                        recent_kd_golden = signal_summary['kd_golden_cross'][-1]
                        st.success(f"🟢 KD金叉")
                        st.caption(f"{recent_kd_golden[0].strftime('%m/%d')}")
                    elif signal_summary['kd_death_cross']:
                        recent_kd_death = signal_summary['kd_death_cross'][-1]
                        st.error(f"🔴 KD死叉")
                        st.caption(f"{recent_kd_death[0].strftime('%m/%d')}")
                
                with col4:
                    st.markdown("### MACD 訊號")
                    if signal_summary['macd_golden_cross']:
                        recent_macd_golden = signal_summary['macd_golden_cross'][-1]
                        st.success(f"🟢 MACD金叉")
                        st.caption(f"最近: {recent_macd_golden[0].strftime('%Y-%m-%d')}")
                    elif signal_summary['macd_death_cross']:
                        recent_macd_death = signal_summary['macd_death_cross'][-1]
                        st.error(f"🔴 MACD死叉")
                        st.caption(f"最近: {recent_macd_death[0].strftime('%Y-%m-%d')}")
                    else:
                        st.info("⚪ 無明顯訊號")
                
                st.divider()
                
                # 顯示最新價格資訊
                st.subheader("💰 最新價格資訊")
                latest = stock_data.iloc[-1]
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("收盤價", f"NT$ {latest['close']:.2f}")
                with col2:
                    change = latest['close'] - stock_data.iloc[-2]['close']
                    change_pct = (change / stock_data.iloc[-2]['close']) * 100
                    st.metric("漲跌", f"{change:+.2f}", f"{change_pct:+.2f}%")
                with col3:
                    st.metric("成交量", f"{int(latest['volume']):,}")
                with col4:
                    st.metric("昨收", f"NT$ {yesterday_close_value:.2f}")
            
            # Tab 2: 技術指標
            with tab2:
                st.subheader(f"📊 {display_name} 技術指標詳情")
                
                latest = stock_data.iloc[-1]
                
                # 移動平均線
                st.markdown("### 📈 移動平均線")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    ma5 = latest.get('MA5', 0)
                    ma5_diff = ((latest['close'] - ma5) / ma5 * 100) if ma5 > 0 else 0
                    st.metric("MA5", f"NT$ {ma5:.2f}", f"{ma5_diff:+.2f}%")
                
                with col2:
                    ma10 = latest.get('MA10', 0)
                    ma10_diff = ((latest['close'] - ma10) / ma10 * 100) if ma10 > 0 else 0
                    st.metric("MA10", f"NT$ {ma10:.2f}", f"{ma10_diff:+.2f}%")
                
                with col3:
                    ma20 = latest.get('MA20', 0)
                    ma20_diff = ((latest['close'] - ma20) / ma20 * 100) if ma20 > 0 else 0
                    st.metric("MA20", f"NT$ {ma20:.2f}", f"{ma20_diff:+.2f}%")
                
                with col4:
                    ma60 = latest.get('MA60', 0)
                    ma60_diff = ((latest['close'] - ma60) / ma60 * 100) if ma60 > 0 else 0
                    st.metric("MA60", f"NT$ {ma60:.2f}", f"{ma60_diff:+.2f}%")
                
                st.divider()
                
                # RSI & KD
                st.markdown("### 📊 動能指標")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    rsi = latest.get('RSI', 0)
                    rsi_status = "🔴 超買" if rsi > 70 else "🟢 超賣" if rsi < 30 else "⚪ 中性"
                    st.metric("RSI", f"{rsi:.2f}", rsi_status)
                
                with col2:
                    k_value = latest.get('KD_K', 0)
                    k_status = "🔴 超買" if k_value > 80 else "🟢 超賣" if k_value < 20 else "⚪ 中性"
                    st.metric("KD-K", f"{k_value:.2f}", k_status)
                
                with col3:
                    d_value = latest.get('KD_D', 0)
                    st.metric("KD-D", f"{d_value:.2f}")
                
                with col4:
                    kd_diff = k_value - d_value
                    kd_signal = "🟢 金叉" if kd_diff > 0 else "🔴 死叉"
                    st.metric("KD差值", f"{kd_diff:.2f}", kd_signal)
                
                st.divider()
                
                # MACD
                st.markdown("### 📉 MACD 指標")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    macd = latest.get('MACD', 0)
                    st.metric("MACD", f"{macd:.2f}")
                
                with col2:
                    macd_signal = latest.get('MACD_signal', 0)
                    st.metric("Signal", f"{macd_signal:.2f}")
                
                with col3:
                    macd_hist = latest.get('MACD_hist', 0)
                    macd_trend = "🟢 多頭" if macd_hist > 0 else "🔴 空頭"
                    st.metric("柱狀圖", f"{macd_hist:.2f}", macd_trend)
                
                st.divider()
                
                # 布林通道
                st.markdown("### 📊 布林通道")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    bb_upper = latest.get('BB_upper', 0)
                    st.metric("上軌", f"NT$ {bb_upper:.2f}")
                
                with col2:
                    bb_middle = latest.get('BB_middle', 0)
                    st.metric("中軌", f"NT$ {bb_middle:.2f}")
                
                with col3:
                    bb_lower = latest.get('BB_lower', 0)
                    st.metric("下軌", f"NT$ {bb_lower:.2f}")
                
                with col4:
                    bb_width = latest.get('BB_width', 0)
                    bb_status = "📈 擴張" if bb_width > 0.1 else "📉 收斂"
                    st.metric("通道寬度", f"{bb_width:.4f}", bb_status)
                
                st.divider()
                
                # 🆕 當沖專用指標
                st.markdown("### 🎯 當沖專用指標")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    williams = latest.get('Williams_R', 0)
                    williams_status = "🔴 超買" if williams > -20 else "🟢 超賣" if williams < -80 else "⚪ 中性"
                    st.metric("Williams %R", f"{williams:.2f}", williams_status)
                
                with col2:
                    atr = latest.get('ATR', 0)
                    atr_pct = latest.get('ATR_percent', 0)
                    st.metric("ATR (波動度)", f"NT$ {atr:.2f}", f"{atr_pct:.2f}%")
                
                with col3:
                    adx = latest.get('ADX', 0)
                    adx_status = "📈 強趨勢" if adx > 25 else "📊 弱趨勢"
                    st.metric("ADX", f"{adx:.2f}", adx_status)
                
                with col4:
                    cci = latest.get('CCI', 0)
                    cci_status = "🔴 超買" if cci > 100 else "🟢 超賣" if cci < -100 else "⚪ 中性"
                    st.metric("CCI", f"{cci:.2f}", cci_status)
                
                st.divider()
                
                # 🆕 止損止盈建議
                st.markdown("### 🎯 止損止盈建議（基於 ATR）")
                
                if 'ATR' in stock_data.columns and latest.get('ATR', 0) > 0:
                    sl_tp = calculate_stop_loss_take_profit(
                        latest['close'],
                        latest['ATR'],
                        risk_reward_ratio=2
                    )
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("建議止損", f"NT$ {sl_tp['stop_loss']:.2f}", 
                                 f"-{sl_tp['risk_amount']:.2f}")
                    
                    with col2:
                        st.metric("建議止盈", f"NT$ {sl_tp['take_profit']:.2f}", 
                                 f"+{sl_tp['reward_amount']:.2f}")
                    
                    with col3:
                        st.metric("保守止損", f"NT$ {sl_tp['conservative_stop']:.2f}")
                    
                    with col4:
                        st.metric("風險報酬比", f"1:{sl_tp['risk_reward_ratio']}")
                else:
                    st.warning("⚠️ ATR 數據不足，無法計算止損止盈")
                
                st.divider()
                
                # 🆕 當沖訊號摘要
                st.markdown("### 🚦 當沖訊號摘要")
                
                daytrading_signals = get_daytrading_signals(stock_data)
                
                if daytrading_signals:
                    col1, col2 = st.columns([1, 3])
                    
                    with col1:
                        recommendation = daytrading_signals['recommendation']
                        strength = daytrading_signals['strength']
                        
                        if recommendation == 'STRONG_BUY':
                            st.success(f"### 🟢 強力買進")
                            st.metric("訊號強度", f"{strength}/100")
                        elif recommendation == 'BUY':
                            st.info(f"### 🔵 買進")
                            st.metric("訊號強度", f"{strength}/100")
                        elif recommendation == 'STRONG_SELL':
                            st.error(f"### 🔴 強力賣出")
                            st.metric("訊號強度", f"{strength}/100")
                        elif recommendation == 'SELL':
                            st.warning(f"### 🟠 賣出")
                            st.metric("訊號強度", f"{strength}/100")
                        else:
                            st.info(f"### ⚪ 觀望")
                            st.metric("訊號強度", f"{strength}/100")
                    
                    with col2:
                        st.markdown("**觸發訊號：**")
                        if daytrading_signals['signals']:
                            for signal in daytrading_signals['signals']:
                                st.write(f"• {signal}")
                        else:
                            st.info("目前無明顯訊號")
                else:
                    st.warning("⚠️ 無法生成當沖訊號")
                
                st.divider()
                
                # 支撐壓力位
                st.markdown("### 📍 支撐壓力位")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**🔴 壓力位**")
                    if support_resistance['resistance']:
                        for i, r in enumerate(support_resistance['resistance'], 1):
                            distance = ((r['price'] - latest['close']) / latest['close'] * 100)
                            st.write(f"{i}. NT$ {r['price']:.2f} ({distance:+.2f}%) - {r['desc']}")
                    else:
                        st.info("無明顯壓力位")
                
                with col2:
                    st.markdown("**🟢 支撐位**")
                    if support_resistance['support']:
                        for i, s in enumerate(support_resistance['support'], 1):
                            distance = ((s['price'] - latest['close']) / latest['close'] * 100)
                            st.write(f"{i}. NT$ {s['price']:.2f} ({distance:+.2f}%) - {s['desc']}")
                    else:
                        st.info("無明顯支撐位")
            
            # Tab 3: 籌碼分析
            with tab3:
                st.subheader(f"💼 {display_name} 三大法人買賣超")
                
                if institutional_data is not None and not institutional_data.empty:
                    # 顯示統計摘要
                    st.markdown("### 📊 近期籌碼統計 (最近10天)")
                    
                    recent_data = institutional_data.head(10)
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        foreign_sum = recent_data['Foreign_Investor'].sum()
                        st.metric(
                            "外資買賣超", 
                            f"{foreign_sum:,.0f} 張",
                            delta="買超" if foreign_sum > 0 else "賣超" if foreign_sum < 0 else "持平"
                        )
                    
                    with col2:
                        trust_sum = recent_data['Investment_Trust'].sum()
                        st.metric(
                            "投信買賣超", 
                            f"{trust_sum:,.0f} 張",
                            delta="買超" if trust_sum > 0 else "賣超" if trust_sum < 0 else "持平"
                        )
                    
                    with col3:
                        dealer_sum = recent_data['Dealer_Total'].sum()
                        st.metric(
                            "自營商買賣超", 
                            f"{dealer_sum:,.0f} 張",
                            delta="買超" if dealer_sum > 0 else "賣超" if dealer_sum < 0 else "持平"
                        )
                    
                    with col4:
                        total_sum = recent_data['Total'].sum()
                        st.metric(
                            "三大法人合計", 
                            f"{total_sum:,.0f} 張",
                            delta="買超" if total_sum > 0 else "賣超" if total_sum < 0 else "持平"
                        )
                    
                    st.divider()
                    
                    # 顯示詳細數據表格
                    st.markdown("### 📋 詳細買賣超記錄")
                    
                    # 格式化顯示
                    display_df = recent_data.copy()
                    display_df['date'] = display_df['date'].dt.strftime('%Y-%m-%d')
                    
                    # 重新命名欄位
                    display_df = display_df.rename(columns={
                        'date': '日期',
                        'Foreign_Investor': '外資',
                        'Investment_Trust': '投信',
                        'Dealer_Self': '自營商(自行)',
                        'Dealer_Hedging': '自營商(避險)',
                        'Dealer_Total': '自營商合計',
                        'Total': '三大法人合計'
                    })
                    
                    st.dataframe(
                        display_df,
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.warning("⚠️ 無籌碼數據")
            
            # Tab 4: 新聞事件（條件式顯示）
            if tab4 is not None:
                with tab4:
                    st.subheader(f"📰 {display_name} 近期新聞事件")
                    
                    if news_result:
                        if news_result.get('is_fallback', False):
                            st.warning("⚠️ 新聞搜尋暫時無法使用")
                        
                        st.markdown(news_result.get('content', '無新聞資料'))
                    else:
                        st.info("📭 目前無重大新聞事件")
            
            # Tab 5: AI 分析報告
            with tab5:
                st.subheader(f"🤖 {display_name} AI 當沖分析報告")
                
                # 顯示分析模式標籤
                if use_news_analysis:
                    st.success("✅ 完整分析模式（含新聞面）")
                else:
                    st.info("⚡ 快速分析模式（僅技術面 + 籌碼面）")
                
                st.markdown(ai_analysis)
                
                # 下載報告按鈕
                st.download_button(
                    label="📥 下載分析報告",
                    data=ai_analysis,
                    file_name=f"{stock_code}_daytrading_analysis_{datetime.now().strftime('%Y%m%d')}.md",
                    mime="text/markdown",
                    use_container_width=True
                )
        
        except Exception as e:
            st.error(f"❌ 分析過程發生錯誤: {str(e)}")
            import traceback
            st.code(traceback.format_exc())

# 頁面底部資訊
st.divider()

# 資料庫狀態顯示
if show_stats:
    with st.expander("📊 資料庫狀態", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("查詢統計（最近30天）")
            stats_df = db.get_query_statistics(days=30)
            if not stats_df.empty:
                st.dataframe(stats_df, use_container_width=True)
            else:
                st.info("尚無查詢記錄")
        
        with col2:
            st.subheader("資料庫資訊")
            
            # 查詢資料庫大小
            if os.path.exists("stock_data.db"):
                db_size = os.path.getsize("stock_data.db") / (1024 * 1024)  # MB
                st.metric("資料庫大小", f"{db_size:.2f} MB")
            
            # 查詢記錄數
            try:
                cursor = db.cursor
                cursor.execute("SELECT COUNT(*) FROM stock_prices")
                price_count = cursor.fetchone()[0]
                st.metric("價格記錄數", f"{price_count:,}")
                
                cursor.execute("SELECT COUNT(DISTINCT symbol) FROM stock_prices")
                symbol_count = cursor.fetchone()[0]
                st.metric("已快取股票數", f"{symbol_count}")
            except Exception as e:
                st.error(f"資料庫查詢錯誤: {str(e)}")

st.markdown("""
<div style='text-align: center; color: gray;'>
    <p>AI 台股當沖分析系統 v2.3（增強版）| Powered by FinMind & Perplexity.ai</p>
    <p>© 2024 Harry_Chung. All rights reserved.</p>
</div>
""", unsafe_allow_html=True)
