#from src.data_providers.yfinance_provider import YFinanceProvider
#yf = YFinanceProvider()
import yfinance as yf
tickers = ['VTI']
start_date = '2014-06-15'
end_date = '2023-12-31'
tickers_str = " ".join(tickers)
ohlcv = yf.download(tickers_str, start=start_date, end=end_date,
                    group_by='ticker', auto_adjust=True, progress=False)
#ohlcv = yf.fetch_ohlcv(tickers, start_date, end_date)
print(ohlcv.head())

