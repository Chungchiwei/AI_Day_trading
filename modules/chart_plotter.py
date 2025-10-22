"""
圖表繪製模組 - 使用 Plotly 繪製專業 K 線圖（增強版）
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

def detect_ma_crossovers(df):
    """
    偵測均線交叉訊號
    
    返回:
        golden_cross: 黃金交叉點列表 [(date, price), ...]
        death_cross: 死亡交叉點列表 [(date, price), ...]
    """
    golden_cross = []
    death_cross = []
    
    if 'MA5' in df.columns and 'MA20' in df.columns:
        for i in range(1, len(df)):
            # 黃金交叉：短期均線向上突破長期均線
            if (df['MA5'].iloc[i-1] <= df['MA20'].iloc[i-1] and 
                df['MA5'].iloc[i] > df['MA20'].iloc[i]):
                golden_cross.append((df['date'].iloc[i], df['close'].iloc[i]))
            
            # 死亡交叉：短期均線向下跌破長期均線
            if (df['MA5'].iloc[i-1] >= df['MA20'].iloc[i-1] and 
                df['MA5'].iloc[i] < df['MA20'].iloc[i]):
                death_cross.append((df['date'].iloc[i], df['close'].iloc[i]))
    
    return golden_cross, death_cross


def detect_kd_crossovers(df):
    """
    偵測 KD 交叉訊號
    
    返回:
        kd_golden: KD 黃金交叉點列表
        kd_death: KD 死亡交叉點列表
    """
    kd_golden = []
    kd_death = []
    
    if 'KD_K' in df.columns and 'KD_D' in df.columns:
        for i in range(1, len(df)):
            # K 值向上突破 D 值
            if (df['KD_K'].iloc[i-1] <= df['KD_D'].iloc[i-1] and 
                df['KD_K'].iloc[i] > df['KD_D'].iloc[i]):
                kd_golden.append((df['date'].iloc[i], df['KD_K'].iloc[i]))
            
            # K 值向下跌破 D 值
            if (df['KD_K'].iloc[i-1] >= df['KD_D'].iloc[i-1] and 
                df['KD_K'].iloc[i] < df['KD_D'].iloc[i]):
                kd_death.append((df['date'].iloc[i], df['KD_K'].iloc[i]))
    
    return kd_golden, kd_death


def detect_macd_crossovers(df):
    """
    偵測 MACD 交叉訊號
    """
    macd_golden = []
    macd_death = []
    
    if 'MACD' in df.columns and 'MACD_signal' in df.columns:
        for i in range(1, len(df)):
            # MACD 向上突破訊號線
            if (df['MACD'].iloc[i-1] <= df['MACD_signal'].iloc[i-1] and 
                df['MACD'].iloc[i] > df['MACD_signal'].iloc[i]):
                macd_golden.append((df['date'].iloc[i], df['MACD'].iloc[i]))
            
            # MACD 向下跌破訊號線
            if (df['MACD'].iloc[i-1] >= df['MACD_signal'].iloc[i-1] and 
                df['MACD'].iloc[i] < df['MACD_signal'].iloc[i]):
                macd_death.append((df['date'].iloc[i], df['MACD'].iloc[i]))
    
    return macd_golden, macd_death


def plot_candlestick_chart(df, symbol, stock_name=None):
    """
    繪製專業 K 線圖與技術指標（增強版）
    
    參數:
        df: 包含 OHLCV 和技術指標的 DataFrame
        symbol: 股票代碼
        stock_name: 股票中文名稱（可選）
    
    返回:
        Plotly Figure 物件
    """
    # ✅ 確保 date 欄位存在
    if 'date' not in df.columns:
        if df.index.name == 'date' or isinstance(df.index, pd.DatetimeIndex):
            df = df.reset_index()
        else:
            raise ValueError("DataFrame 缺少 'date' 欄位")
    
    # ✅ 確保 date 是 datetime 格式
    if not pd.api.types.is_datetime64_any_dtype(df['date']):
        df['date'] = pd.to_datetime(df['date'])
    
    # 建立標題
    if stock_name:
        title = f"{stock_name} ({symbol}) 技術分析圖表"
    else:
        title = f"{symbol} 技術分析圖表"
    
    # 偵測交叉訊號
    ma_golden, ma_death = detect_ma_crossovers(df)
    kd_golden, kd_death = detect_kd_crossovers(df)
    macd_golden, macd_death = detect_macd_crossovers(df)
    
    # 🆕 建立子圖（增加到 8 個）
    fig = make_subplots(
        rows=8, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.015,
        subplot_titles=(
            title, 
            '成交量 (Volume)', 
            'MACD 指標', 
            'RSI & Williams %R', 
            'KD 隨機指標',
            'ADX 趨勢強度',
            'CCI 順勢指標',
            'OBV 能量潮'
        ),
        row_heights=[0.35, 0.10, 0.10, 0.10, 0.10, 0.08, 0.08, 0.09],
        specs=[
            [{"secondary_y": False}],  # K線圖
            [{"secondary_y": False}],  # 成交量
            [{"secondary_y": False}],  # MACD
            [{"secondary_y": True}],   # RSI & Williams %R
            [{"secondary_y": False}],  # KD
            [{"secondary_y": False}],  # ADX
            [{"secondary_y": False}],  # CCI
            [{"secondary_y": True}]    # OBV
        ]
    )
    
    # ==================== 1. K線圖 ====================
    fig.add_trace(
        go.Candlestick(
            x=df['date'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='K線',
            increasing_line_color='#FF4444',
            decreasing_line_color='#00AA00',
            increasing_fillcolor='#FF4444',
            decreasing_fillcolor='#00AA00',
            line=dict(width=1)
        ),
        row=1, col=1
    )
    
    # 移動平均線
    ma_configs = {
        'MA5': {'color': '#FF6B6B', 'width': 1.5, 'dash': 'solid'},
        'MA10': {'color': '#4ECDC4', 'width': 1.5, 'dash': 'solid'},
        'MA20': {'color': '#45B7D1', 'width': 2, 'dash': 'solid'},
        'MA60': {'color': '#FFA07A', 'width': 2, 'dash': 'dash'}
    }
    
    for ma, config in ma_configs.items():
        if ma in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df['date'],
                    y=df[ma],
                    name=ma,
                    line=dict(
                        color=config['color'],
                        width=config['width'],
                        dash=config['dash']
                    ),
                    opacity=0.8
                ),
                row=1, col=1
            )
    
    # 🆕 VWAP（成交量加權平均價）
    if 'VWAP' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['VWAP'],
                name='VWAP',
                line=dict(color='#9C27B0', width=2, dash='dot'),
                opacity=0.7
            ),
            row=1, col=1
        )
    
    # 🆕 SAR 拋物線指標
    if 'SAR' in df.columns:
        # 分離上升和下降 SAR
        sar_up = df['SAR'].where(df['SAR'] < df['close'])
        sar_down = df['SAR'].where(df['SAR'] > df['close'])
        
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=sar_up,
                mode='markers',
                name='SAR(多)',
                marker=dict(symbol='circle', size=4, color='green'),
                showlegend=True
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=sar_down,
                mode='markers',
                name='SAR(空)',
                marker=dict(symbol='circle', size=4, color='red'),
                showlegend=True
            ),
            row=1, col=1
        )
    
    # 布林通道
    if all(col in df.columns for col in ['BB_upper', 'BB_middle', 'BB_lower']):
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['BB_upper'],
                name='BB上軌',
                line=dict(color='rgba(128, 128, 128, 0.3)', width=1, dash='dash'),
                showlegend=True
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['BB_middle'],
                name='BB中軌',
                line=dict(color='rgba(100, 100, 255, 0.5)', width=1.5),
                showlegend=True
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['BB_lower'],
                name='BB下軌',
                line=dict(color='rgba(128, 128, 128, 0.3)', width=1, dash='dash'),
                fill='tonexty',
                fillcolor='rgba(128, 128, 255, 0.1)',
                showlegend=True
            ),
            row=1, col=1
        )
    
    # 標記均線黃金交叉
    if ma_golden:
        dates, prices = zip(*ma_golden)
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=prices,
                mode='markers',
                name='黃金交叉',
                marker=dict(
                    symbol='triangle-up',
                    size=15,
                    color='gold',
                    line=dict(color='red', width=2)
                ),
                showlegend=True
            ),
            row=1, col=1
        )
    
    # 標記均線死亡交叉
    if ma_death:
        dates, prices = zip(*ma_death)
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=prices,
                mode='markers',
                name='死亡交叉',
                marker=dict(
                    symbol='triangle-down',
                    size=15,
                    color='black',
                    line=dict(color='white', width=2)
                ),
                showlegend=True
            ),
            row=1, col=1
        )
    
    # ==================== 2. 成交量 ====================
    if 'volume' in df.columns:
        colors = ['red' if close >= open else 'green' 
                  for close, open in zip(df['close'], df['open'])]
        
        fig.add_trace(
            go.Bar(
                x=df['date'],
                y=df['volume'],
                name='成交量',
                marker_color=colors,
                opacity=0.6,
                showlegend=True
            ),
            row=2, col=1
        )
        
        # 成交量移動平均線
        if 'Volume_MA5' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df['date'],
                    y=df['Volume_MA5'],
                    name='量MA5',
                    line=dict(color='orange', width=2),
                    showlegend=True
                ),
                row=2, col=1
            )
        
        if 'Volume_MA20' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df['date'],
                    y=df['Volume_MA20'],
                    name='量MA20',
                    line=dict(color='purple', width=2, dash='dash'),
                    showlegend=True
                ),
                row=2, col=1
            )
    
    # ==================== 3. MACD ====================
    if 'MACD' in df.columns and 'MACD_signal' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['MACD'],
                name='MACD',
                line=dict(color='#2E86DE', width=2),
                showlegend=True
            ),
            row=3, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['MACD_signal'],
                name='Signal',
                line=dict(color='#EE5A6F', width=2),
                showlegend=True
            ),
            row=3, col=1
        )
        
        if 'MACD_hist' in df.columns:
            colors = ['#FF6B6B' if val >= 0 else '#51CF66' for val in df['MACD_hist']]
            fig.add_trace(
                go.Bar(
                    x=df['date'],
                    y=df['MACD_hist'],
                    name='MACD柱',
                    marker_color=colors,
                    opacity=0.6,
                    showlegend=True
                ),
                row=3, col=1
            )
        
        # 標記 MACD 交叉
        if macd_golden:
            dates, values = zip(*macd_golden)
            fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=values,
                    mode='markers',
                    name='MACD金叉',
                    marker=dict(symbol='star', size=12, color='gold'),
                    showlegend=True
                ),
                row=3, col=1
            )
        
        if macd_death:
            dates, values = zip(*macd_death)
            fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=values,
                    mode='markers',
                    name='MACD死叉',
                    marker=dict(symbol='x', size=12, color='black'),
                    showlegend=True
                ),
                row=3, col=1
            )
        
        fig.add_hline(y=0, line_dash="solid", line_color="gray", 
                     line_width=1, row=3, col=1)
    
    # ==================== 4. RSI & Williams %R ====================
    if 'RSI' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['RSI'],
                name='RSI',
                line=dict(color='#9C27B0', width=2),
                showlegend=True
            ),
            row=4, col=1, secondary_y=False
        )
        
        # RSI 超買超賣區域
        fig.add_hrect(
            y0=70, y1=100,
            fillcolor="rgba(255, 0, 0, 0.1)",
            line_width=0,
            row=4, col=1
        )
        
        fig.add_hrect(
            y0=0, y1=30,
            fillcolor="rgba(0, 255, 0, 0.1)",
            line_width=0,
            row=4, col=1
        )
        
        # RSI 參考線
        fig.add_hline(y=70, line_dash="dash", line_color="red", 
                     line_width=1, row=4, col=1, secondary_y=False)
        fig.add_hline(y=50, line_dash="dot", line_color="gray", 
                     line_width=1, row=4, col=1, secondary_y=False)
        fig.add_hline(y=30, line_dash="dash", line_color="green", 
                     line_width=1, row=4, col=1, secondary_y=False)
    
    # 🆕 Williams %R
    if 'Williams_R' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['Williams_R'],
                name='Williams %R',
                line=dict(color='#FF9800', width=1.5, dash='dot'),
                showlegend=True
            ),
            row=4, col=1, secondary_y=True
        )
        
        fig.add_hline(y=-20, line_dash="dash", line_color="red", 
                     line_width=1, row=4, col=1, secondary_y=True)
        fig.add_hline(y=-80, line_dash="dash", line_color="green", 
                     line_width=1, row=4, col=1, secondary_y=True)
    
    # ==================== 5. KD 指標 ====================
    if 'KD_K' in df.columns and 'KD_D' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['KD_K'],
                name='K值',
                line=dict(color='#3498DB', width=2),
                showlegend=True
            ),
            row=5, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['KD_D'],
                name='D值',
                line=dict(color='#E74C3C', width=2),
                showlegend=True
            ),
            row=5, col=1
        )
        
        # KD 超買超賣區域
        fig.add_hrect(
            y0=80, y1=100,
            fillcolor="rgba(255, 0, 0, 0.1)",
            line_width=0,
            row=5, col=1
        )
        
        fig.add_hrect(
            y0=0, y1=20,
            fillcolor="rgba(0, 255, 0, 0.1)",
            line_width=0,
            row=5, col=1
        )
        
        # KD 參考線
        fig.add_hline(y=80, line_dash="dash", line_color="red", 
                     line_width=1, row=5, col=1)
        fig.add_hline(y=50, line_dash="dot", line_color="gray", 
                     line_width=1, row=5, col=1)
        fig.add_hline(y=20, line_dash="dash", line_color="green", 
                     line_width=1, row=5, col=1)
        
        # 標記 KD 交叉
        if kd_golden:
            dates, values = zip(*kd_golden)
            fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=values,
                    mode='markers',
                    name='KD金叉',
                    marker=dict(symbol='triangle-up', size=10, color='gold'),
                    showlegend=True
                ),
                row=5, col=1
            )
        
        if kd_death:
            dates, values = zip(*kd_death)
            fig.add_trace(
                go.Scatter(
                    x=dates,
                    y=values,
                    mode='markers',
                    name='KD死叉',
                    marker=dict(symbol='triangle-down', size=10, color='black'),
                    showlegend=True
                ),
                row=5, col=1
            )
    
    # ==================== 6. 🆕 ADX 趨勢強度 ====================
    if 'ADX' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['ADX'],
                name='ADX',
                line=dict(color='#000000', width=2),
                fill='tozeroy',
                fillcolor='rgba(0, 0, 0, 0.1)',
                showlegend=True
            ),
            row=6, col=1
        )
        
        if 'DI_plus' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df['date'],
                    y=df['DI_plus'],
                    name='+DI',
                    line=dict(color='#4CAF50', width=1.5),
                    showlegend=True
                ),
                row=6, col=1
            )
        
        if 'DI_minus' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df['date'],
                    y=df['DI_minus'],
                    name='-DI',
                    line=dict(color='#F44336', width=1.5),
                    showlegend=True
                ),
                row=6, col=1
            )
        
        # ADX 25 參考線（趨勢門檻）
        fig.add_hline(y=25, line_dash="dash", line_color="gray", 
                     line_width=1, annotation_text="趨勢門檻", row=6, col=1)
    
    # ==================== 7. 🆕 CCI 順勢指標 ====================
    if 'CCI' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['CCI'],
                name='CCI',
                line=dict(color='#2196F3', width=2),
                showlegend=True
            ),
            row=7, col=1
        )
        
        # CCI 超買超賣區域
        fig.add_hrect(
            y0=100, y1=300,
            fillcolor="rgba(255, 0, 0, 0.1)",
            line_width=0,
            row=7, col=1
        )
        
        fig.add_hrect(
            y0=-300, y1=-100,
            fillcolor="rgba(0, 255, 0, 0.1)",
            line_width=0,
            row=7, col=1
        )
        
        fig.add_hline(y=100, line_dash="dash", line_color="red", 
                     line_width=1, row=7, col=1)
        fig.add_hline(y=0, line_dash="solid", line_color="gray", 
                     line_width=1, row=7, col=1)
        fig.add_hline(y=-100, line_dash="dash", line_color="green", 
                     line_width=1, row=7, col=1)
    
    # ==================== 8. 🆕 OBV 能量潮 ====================
    if 'OBV' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['OBV'],
                name='OBV',
                line=dict(color='#FF5722', width=2),
                fill='tozeroy',
                fillcolor='rgba(255, 87, 34, 0.1)',
                showlegend=True
            ),
            row=8, col=1, secondary_y=False
        )
        
        if 'OBV_MA5' in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df['date'],
                    y=df['OBV_MA5'],
                    name='OBV MA5',
                    line=dict(color='#795548', width=1.5, dash='dash'),
                    showlegend=True
                ),
                row=8, col=1, secondary_y=False
            )
    
    # 🆕 ATR 波動度（在 OBV 的次軸）
    if 'ATR_percent' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['ATR_percent'],
                name='ATR%',
                line=dict(color='#607D8B', width=1.5, dash='dot'),
                showlegend=True
            ),
            row=8, col=1, secondary_y=True
        )
    
    # ==================== 更新布局 ====================
    fig.update_layout(
        height=1800,  # 增加高度以容納更多子圖
        showlegend=True,
        xaxis_rangeslider_visible=False,
        hovermode='x unified',
        template='plotly_white',
        font=dict(family="Microsoft JhengHei, Arial", size=10),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(255, 255, 255, 0.8)",
            bordercolor="gray",
            borderwidth=1
        ),
        margin=dict(l=50, r=50, t=80, b=50)
    )
    
    # 更新 x 軸格式（隱藏週末）
    fig.update_xaxes(
        rangebreaks=[
            dict(bounds=["sat", "mon"])
        ],
        showgrid=True,
        gridwidth=1,
        gridcolor='rgba(128, 128, 128, 0.2)'
    )
    
    # 更新 y 軸格式
    fig.update_yaxes(
        showgrid=True,
        gridwidth=1,
        gridcolor='rgba(128, 128, 128, 0.2)'
    )
    
    # 設定各子圖的 y 軸標籤
    fig.update_yaxes(title_text="價格 (NT$)", row=1, col=1)
    fig.update_yaxes(title_text="成交量", row=2, col=1)
    fig.update_yaxes(title_text="MACD", row=3, col=1)
    fig.update_yaxes(title_text="RSI", row=4, col=1, secondary_y=False)
    fig.update_yaxes(title_text="Williams %R", row=4, col=1, secondary_y=True)
    fig.update_yaxes(title_text="KD", row=5, col=1)
    fig.update_yaxes(title_text="ADX/DI", row=6, col=1)
    fig.update_yaxes(title_text="CCI", row=7, col=1)
    fig.update_yaxes(title_text="OBV", row=8, col=1, secondary_y=False)
    fig.update_yaxes(title_text="ATR%", row=8, col=1, secondary_y=True)
    
    return fig


def get_signal_summary(df):
    """
    生成技術指標訊號摘要（增強版）
    
    返回:
        dict: 包含各種訊號的字典
    """
    summary = {
        'ma_golden_cross': [],
        'ma_death_cross': [],
        'kd_golden_cross': [],
        'kd_death_cross': [],
        'macd_golden_cross': [],
        'macd_death_cross': [],
        'rsi_overbought': False,
        'rsi_oversold': False,
        'kd_overbought': False,
        'kd_oversold': False,
        'williams_overbought': False,
        'williams_oversold': False,
        'cci_overbought': False,
        'cci_oversold': False,
        'adx_strong_trend': False,
        'obv_divergence': None
    }
    
    # 偵測交叉訊號
    ma_golden, ma_death = detect_ma_crossovers(df)
    kd_golden, kd_death = detect_kd_crossovers(df)
    macd_golden, macd_death = detect_macd_crossovers(df)
    
    summary['ma_golden_cross'] = ma_golden
    summary['ma_death_cross'] = ma_death
    summary['kd_golden_cross'] = kd_golden
    summary['kd_death_cross'] = kd_death
    summary['macd_golden_cross'] = macd_golden
    summary['macd_death_cross'] = macd_death
    
    # 檢查最新狀態
    if len(df) > 0:
        latest = df.iloc[-1]
        
        # RSI
        if 'RSI' in df.columns and not pd.isna(latest['RSI']):
            summary['rsi_overbought'] = latest['RSI'] > 70
            summary['rsi_oversold'] = latest['RSI'] < 30
        
        # KD
        if 'KD_K' in df.columns and not pd.isna(latest['KD_K']):
            summary['kd_overbought'] = latest['KD_K'] > 80
            summary['kd_oversold'] = latest['KD_K'] < 20
        
        # 🆕 Williams %R
        if 'Williams_R' in df.columns and not pd.isna(latest['Williams_R']):
            summary['williams_overbought'] = latest['Williams_R'] > -20
            summary['williams_oversold'] = latest['Williams_R'] < -80
        
        # 🆕 CCI
        if 'CCI' in df.columns and not pd.isna(latest['CCI']):
            summary['cci_overbought'] = latest['CCI'] > 100
            summary['cci_oversold'] = latest['CCI'] < -100
        
        # 🆕 ADX 趨勢強度
        if 'ADX' in df.columns and not pd.isna(latest['ADX']):
            summary['adx_strong_trend'] = latest['ADX'] > 25
        
        # 🆕 OBV 背離檢測
        if 'OBV' in df.columns and len(df) >= 10:
            recent_df = df.tail(10)
            price_trend = recent_df['close'].iloc[-1] > recent_df['close'].iloc[0]
            obv_trend = recent_df['OBV'].iloc[-1] > recent_df['OBV'].iloc[0]
            
            if price_trend and not obv_trend:
                summary['obv_divergence'] = 'bearish'  # 頂背離
            elif not price_trend and obv_trend:
                summary['obv_divergence'] = 'bullish'  # 底背離
    
    return summary


def create_signal_badge(signal_type, value=None):
    """
    🆕 建立訊號徽章 HTML
    
    參數:
        signal_type: 訊號類型 ('buy', 'sell', 'neutral', 'strong_buy', 'strong_sell')
        value: 訊號值（可選）
    
    返回:
        HTML 字串
    """
    badges = {
        'strong_buy': ('🟢 強力買進', '#4CAF50', 'white'),
        'buy': ('🔵 買進', '#2196F3', 'white'),
        'neutral': ('⚪ 中性', '#9E9E9E', 'white'),
        'sell': ('🟠 賣出', '#FF9800', 'white'),
        'strong_sell': ('🔴 強力賣出', '#F44336', 'white')
    }
    
    text, bg_color, text_color = badges.get(signal_type, badges['neutral'])
    
    if value is not None:
        text += f" ({value})"
    
    return f"""
    <div style="
        display: inline-block;
        padding: 8px 16px;
        background-color: {bg_color};
        color: {text_color};
        border-radius: 20px;
        font-weight: bold;
        font-size: 14px;
        margin: 4px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    ">
        {text}
    </div>
    """
