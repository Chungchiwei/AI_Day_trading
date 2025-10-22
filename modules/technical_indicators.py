"""
技術指標計算模組 - 增強版（新增當沖專用指標）
"""

import pandas as pd
import numpy as np
from ta.trend import MACD, SMAIndicator, EMAIndicator, ADXIndicator
from ta.momentum import RSIIndicator, StochasticOscillator, WilliamsRIndicator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import OnBalanceVolumeIndicator, VolumeWeightedAveragePrice
from ta.trend import CCIIndicator, PSARIndicator

def calculate_technical_indicators(df):
    """
    計算所有技術指標（增強版）
    
    參數:
        df: 包含 OHLCV 的 DataFrame
    
    返回:
        添加了技術指標的 DataFrame
    """
    df = df.copy()
    
    # ==================== 移動平均線 ====================
    df['MA5'] = SMAIndicator(close=df['close'], window=5).sma_indicator()
    df['MA10'] = SMAIndicator(close=df['close'], window=10).sma_indicator()
    df['MA20'] = SMAIndicator(close=df['close'], window=20).sma_indicator()
    df['MA60'] = SMAIndicator(close=df['close'], window=60).sma_indicator()
    
    # EMA (指數移動平均)
    df['EMA12'] = EMAIndicator(close=df['close'], window=12).ema_indicator()
    df['EMA26'] = EMAIndicator(close=df['close'], window=26).ema_indicator()
    
    # ==================== 布林通道 ====================
    bollinger = BollingerBands(close=df['close'], window=20, window_dev=2)
    df['BB_upper'] = bollinger.bollinger_hband()
    df['BB_middle'] = bollinger.bollinger_mavg()
    df['BB_lower'] = bollinger.bollinger_lband()
    df['BB_width'] = bollinger.bollinger_wband()  # 通道寬度
    df['BB_pband'] = bollinger.bollinger_pband()  # 價格在通道中的位置 (0-1)
    
    # ==================== MACD ====================
    macd = MACD(close=df['close'], window_slow=26, window_fast=12, window_sign=9)
    df['MACD'] = macd.macd()
    df['MACD_signal'] = macd.macd_signal()
    df['MACD_hist'] = macd.macd_diff()
    
    # ==================== RSI ====================
    rsi = RSIIndicator(close=df['close'], window=14)
    df['RSI'] = rsi.rsi()
    
    # 多週期 RSI
    df['RSI_6'] = RSIIndicator(close=df['close'], window=6).rsi()
    df['RSI_24'] = RSIIndicator(close=df['close'], window=24).rsi()
    
    # ==================== KD 隨機指標 ====================
    stoch = StochasticOscillator(
        high=df['high'],
        low=df['low'],
        close=df['close'],
        window=14,
        smooth_window=3
    )
    df['KD_K'] = stoch.stoch()
    df['KD_D'] = stoch.stoch_signal()
    
    # ==================== 🆕 威廉指標 (Williams %R) ====================
    williams = WilliamsRIndicator(
        high=df['high'],
        low=df['low'],
        close=df['close'],
        lbp=14
    )
    df['Williams_R'] = williams.williams_r()
    
    # ==================== 🆕 ATR (波動度) ====================
    atr = AverageTrueRange(
        high=df['high'],
        low=df['low'],
        close=df['close'],
        window=14
    )
    df['ATR'] = atr.average_true_range()
    df['ATR_percent'] = (df['ATR'] / df['close']) * 100  # ATR 百分比
    
    # ==================== 🆕 OBV (能量潮) ====================
    obv = OnBalanceVolumeIndicator(
        close=df['close'],
        volume=df['volume']
    )
    df['OBV'] = obv.on_balance_volume()
    df['OBV_MA5'] = df['OBV'].rolling(window=5).mean()  # OBV 5日均線
    
    # ==================== 🆕 DMI/ADX (趨勢強度) ====================
    adx = ADXIndicator(
        high=df['high'],
        low=df['low'],
        close=df['close'],
        window=14
    )
    df['ADX'] = adx.adx()
    df['DI_plus'] = adx.adx_pos()   # +DI
    df['DI_minus'] = adx.adx_neg()  # -DI
    
    # ==================== 🆕 CCI (順勢指標) ====================
    cci = CCIIndicator(
        high=df['high'],
        low=df['low'],
        close=df['close'],
        window=20
    )
    df['CCI'] = cci.cci()
    
    # ==================== 🆕 VWAP (成交量加權平均價) ====================
    # 注意：VWAP 通常是當日計算，這裡提供歷史 VWAP
    if 'date' in df.columns:
        df['date_only'] = pd.to_datetime(df['date']).dt.date
        
        # 計算每日 VWAP
        df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
        df['tp_volume'] = df['typical_price'] * df['volume']
        
        # 按日期分組計算 VWAP
        df['cumulative_tp_volume'] = df.groupby('date_only')['tp_volume'].cumsum()
        df['cumulative_volume'] = df.groupby('date_only')['volume'].cumsum()
        df['VWAP'] = df['cumulative_tp_volume'] / df['cumulative_volume']
        
        # 清理臨時欄位
        df.drop(['date_only', 'typical_price', 'tp_volume', 
                'cumulative_tp_volume', 'cumulative_volume'], axis=1, inplace=True)
    
    # ==================== 🆕 乖離率 (BIAS) ====================
    df['BIAS_5'] = ((df['close'] - df['MA5']) / df['MA5']) * 100
    df['BIAS_10'] = ((df['close'] - df['MA10']) / df['MA10']) * 100
    df['BIAS_20'] = ((df['close'] - df['MA20']) / df['MA20']) * 100
    
    # ==================== 🆕 SAR (拋物線指標) ====================
    psar = PSARIndicator(
        high=df['high'],
        low=df['low'],
        close=df['close'],
        step=0.02,
        max_step=0.2
    )
    df['SAR'] = psar.psar()
    df['SAR_up'] = psar.psar_up()
    df['SAR_down'] = psar.psar_down()
    
    # ==================== 🆕 成交量比率 ====================
    df['Volume_MA5'] = df['volume'].rolling(window=5).mean()
    df['Volume_MA20'] = df['volume'].rolling(window=20).mean()
    df['Volume_Ratio'] = (df['volume'] / df['Volume_MA20']) * 100  # 當日量 / 20日均量
    
    # ==================== 🆕 價格動能 (ROC) ====================
    df['ROC_5'] = ((df['close'] - df['close'].shift(5)) / df['close'].shift(5)) * 100
    df['ROC_10'] = ((df['close'] - df['close'].shift(10)) / df['close'].shift(10)) * 100
    
    # ==================== 🆕 真實波幅百分比 ====================
    df['True_Range'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['close'].shift(1)),
            abs(df['low'] - df['close'].shift(1))
        )
    )
    df['TR_percent'] = (df['True_Range'] / df['close']) * 100
    
    return df


def calculate_support_resistance(df, num_levels=3):
    """
    計算支撐壓力位（增強版）
    
    參數:
        df: 包含技術指標的 DataFrame
        num_levels: 要計算的支撐/壓力位數量
    
    返回:
        dict: 包含支撐位和壓力位的字典
    """
    latest = df.iloc[-1]
    current_price = latest['close']
    
    support_levels = []
    resistance_levels = []
    
    # 1. 移動平均線作為支撐壓力
    ma_levels = {
        'MA5': latest.get('MA5', 0),
        'MA10': latest.get('MA10', 0),
        'MA20': latest.get('MA20', 0),
        'MA60': latest.get('MA60', 0)
    }
    
    for ma_name, ma_value in ma_levels.items():
        if pd.notna(ma_value) and ma_value > 0:
            if ma_value < current_price:
                support_levels.append({
                    'price': ma_value,
                    'desc': f'{ma_name} 支撐',
                    'strength': 'medium'
                })
            elif ma_value > current_price:
                resistance_levels.append({
                    'price': ma_value,
                    'desc': f'{ma_name} 壓力',
                    'strength': 'medium'
                })
    
    # 2. 布林通道
    bb_upper = latest.get('BB_upper', 0)
    bb_lower = latest.get('BB_lower', 0)
    
    if pd.notna(bb_upper) and bb_upper > current_price:
        resistance_levels.append({
            'price': bb_upper,
            'desc': '布林上軌壓力',
            'strength': 'strong'
        })
    
    if pd.notna(bb_lower) and bb_lower < current_price:
        support_levels.append({
            'price': bb_lower,
            'desc': '布林下軌支撐',
            'strength': 'strong'
        })
    
    # 3. 🆕 SAR 指標
    sar_value = latest.get('SAR', 0)
    if pd.notna(sar_value) and sar_value > 0:
        if sar_value < current_price:
            support_levels.append({
                'price': sar_value,
                'desc': 'SAR 追蹤止損',
                'strength': 'strong'
            })
        else:
            resistance_levels.append({
                'price': sar_value,
                'desc': 'SAR 壓力',
                'strength': 'strong'
            })
    
    # 4. 🆕 VWAP
    vwap_value = latest.get('VWAP', 0)
    if pd.notna(vwap_value) and vwap_value > 0:
        if vwap_value < current_price:
            support_levels.append({
                'price': vwap_value,
                'desc': 'VWAP 平均成本支撐',
                'strength': 'strong'
            })
        else:
            resistance_levels.append({
                'price': vwap_value,
                'desc': 'VWAP 平均成本壓力',
                'strength': 'strong'
            })
    
    # 5. 近期高低點（使用最近 20 天數據）
    recent_data = df.tail(20)
    
    # 找出局部高點
    for i in range(1, len(recent_data) - 1):
        if (recent_data.iloc[i]['high'] > recent_data.iloc[i-1]['high'] and
            recent_data.iloc[i]['high'] > recent_data.iloc[i+1]['high'] and
            recent_data.iloc[i]['high'] > current_price):
            resistance_levels.append({
                'price': recent_data.iloc[i]['high'],
                'desc': f'近期高點 ({recent_data.iloc[i]["date"].strftime("%m/%d")})',
                'strength': 'medium'
            })
    
    # 找出局部低點
    for i in range(1, len(recent_data) - 1):
        if (recent_data.iloc[i]['low'] < recent_data.iloc[i-1]['low'] and
            recent_data.iloc[i]['low'] < recent_data.iloc[i+1]['low'] and
            recent_data.iloc[i]['low'] < current_price):
            support_levels.append({
                'price': recent_data.iloc[i]['low'],
                'desc': f'近期低點 ({recent_data.iloc[i]["date"].strftime("%m/%d")})',
                'strength': 'medium'
            })
    
    # 6. 🆕 ATR 動態支撐壓力
    atr_value = latest.get('ATR', 0)
    if pd.notna(atr_value) and atr_value > 0:
        # 基於 ATR 的動態止損點
        support_levels.append({
            'price': current_price - (atr_value * 2),
            'desc': 'ATR 2倍止損點',
            'strength': 'strong'
        })
        
        resistance_levels.append({
            'price': current_price + (atr_value * 2),
            'desc': 'ATR 2倍目標價',
            'strength': 'medium'
        })
    
    # 排序並去重
    support_levels = sorted(support_levels, key=lambda x: x['price'], reverse=True)
    resistance_levels = sorted(resistance_levels, key=lambda x: x['price'])
    
    # 去除相近的價位（差距小於 0.5%）
    def remove_close_levels(levels, tolerance=0.005):
        if not levels:
            return []
        
        filtered = [levels[0]]
        for level in levels[1:]:
            if abs(level['price'] - filtered[-1]['price']) / filtered[-1]['price'] > tolerance:
                filtered.append(level)
        return filtered
    
    support_levels = remove_close_levels(support_levels)
    resistance_levels = remove_close_levels(resistance_levels)
    
    # 限制數量
    support_levels = support_levels[:num_levels]
    resistance_levels = resistance_levels[:num_levels]
    
    return {
        'support': support_levels,
        'resistance': resistance_levels,
        'current_price': current_price
    }


def get_daytrading_signals(df):
    """
    🆕 生成當沖交易訊號
    
    返回:
        dict: 包含各種交易訊號的字典
    """
    if df.empty or len(df) < 2:
        return None
    
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    signals = {
        'timestamp': latest.get('date'),
        'price': latest['close'],
        'signals': [],
        'strength': 0,  # -100 到 +100
        'recommendation': 'HOLD'
    }
    
    strength_score = 0
    
    # 1. MACD 訊號
    if latest['MACD'] > latest['MACD_signal'] and prev['MACD'] <= prev['MACD_signal']:
        signals['signals'].append('MACD 金叉 (買進)')
        strength_score += 15
    elif latest['MACD'] < latest['MACD_signal'] and prev['MACD'] >= prev['MACD_signal']:
        signals['signals'].append('MACD 死叉 (賣出)')
        strength_score -= 15
    
    # 2. KD 訊號
    if latest['KD_K'] > latest['KD_D'] and prev['KD_K'] <= prev['KD_D']:
        if latest['KD_K'] < 30:
            signals['signals'].append('KD 低檔金叉 (強買)')
            strength_score += 20
        else:
            signals['signals'].append('KD 金叉 (買進)')
            strength_score += 10
    elif latest['KD_K'] < latest['KD_D'] and prev['KD_K'] >= prev['KD_D']:
        if latest['KD_K'] > 70:
            signals['signals'].append('KD 高檔死叉 (強賣)')
            strength_score -= 20
        else:
            signals['signals'].append('KD 死叉 (賣出)')
            strength_score -= 10
    
    # 3. RSI 訊號
    if latest['RSI'] < 30:
        signals['signals'].append('RSI 超賣 (買進)')
        strength_score += 15
    elif latest['RSI'] > 70:
        signals['signals'].append('RSI 超買 (賣出)')
        strength_score -= 15
    
    # 4. 🆕 威廉指標
    if latest['Williams_R'] > -20:
        signals['signals'].append('Williams %R 超買 (賣出)')
        strength_score -= 10
    elif latest['Williams_R'] < -80:
        signals['signals'].append('Williams %R 超賣 (買進)')
        strength_score += 10
    
    # 5. 🆕 ADX 趨勢強度
    if latest['ADX'] > 25:
        if latest['DI_plus'] > latest['DI_minus']:
            signals['signals'].append('ADX 強勢上漲趨勢')
            strength_score += 10
        else:
            signals['signals'].append('ADX 強勢下跌趨勢')
            strength_score -= 10
    
    # 6. 🆕 CCI 訊號
    if latest['CCI'] > 100:
        signals['signals'].append('CCI 超買 (賣出)')
        strength_score -= 10
    elif latest['CCI'] < -100:
        signals['signals'].append('CCI 超賣 (買進)')
        strength_score += 10
    
    # 7. 🆕 OBV 背離
    if len(df) >= 5:
        price_trend = latest['close'] > df.iloc[-5]['close']
        obv_trend = latest['OBV'] > df.iloc[-5]['OBV']
        
        if price_trend and not obv_trend:
            signals['signals'].append('⚠️ OBV 頂背離 (賣出)')
            strength_score -= 15
        elif not price_trend and obv_trend:
            signals['signals'].append('✅ OBV 底背離 (買進)')
            strength_score += 15
    
    # 8. 🆕 布林通道突破
    if latest['close'] > latest['BB_upper']:
        signals['signals'].append('突破布林上軌 (強勢/超買)')
        strength_score += 5
    elif latest['close'] < latest['BB_lower']:
        signals['signals'].append('跌破布林下軌 (弱勢/超賣)')
        strength_score -= 5
    
    # 9. 🆕 成交量異常
    if latest['Volume_Ratio'] > 150:
        signals['signals'].append('🔥 成交量爆量 (注意)')
        strength_score += 5
    
    # 10. 🆕 價格動能
    if latest['ROC_5'] > 5:
        signals['signals'].append('短期動能強勁')
        strength_score += 10
    elif latest['ROC_5'] < -5:
        signals['signals'].append('短期動能疲弱')
        strength_score -= 10
    
    # 綜合判斷
    signals['strength'] = max(min(strength_score, 100), -100)
    
    if strength_score >= 30:
        signals['recommendation'] = 'STRONG_BUY'
    elif strength_score >= 15:
        signals['recommendation'] = 'BUY'
    elif strength_score <= -30:
        signals['recommendation'] = 'STRONG_SELL'
    elif strength_score <= -15:
        signals['recommendation'] = 'SELL'
    else:
        signals['recommendation'] = 'HOLD'
    
    return signals


def calculate_stop_loss_take_profit(current_price, atr, risk_reward_ratio=2):
    """
    🆕 基於 ATR 計算止損止盈點
    
    參數:
        current_price: 當前價格
        atr: ATR 值
        risk_reward_ratio: 風險報酬比 (預設 1:2)
    
    返回:
        dict: 止損止盈建議
    """
    # 止損：當前價 - 2 倍 ATR
    stop_loss = current_price - (atr * 2)
    
    # 止盈：當前價 + (2 倍 ATR * 風險報酬比)
    take_profit = current_price + (atr * 2 * risk_reward_ratio)
    
    # 保守止損（1.5 倍 ATR）
    conservative_stop = current_price - (atr * 1.5)
    
    # 激進止損（2.5 倍 ATR）
    aggressive_stop = current_price - (atr * 2.5)
    
    return {
        'stop_loss': round(stop_loss, 2),
        'take_profit': round(take_profit, 2),
        'conservative_stop': round(conservative_stop, 2),
        'aggressive_stop': round(aggressive_stop, 2),
        'risk_amount': round(current_price - stop_loss, 2),
        'reward_amount': round(take_profit - current_price, 2),
        'risk_reward_ratio': risk_reward_ratio
    }
