import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import logging

logger = logging.getLogger(__name__)

class TearsheetGenerator:
    def __init__(self, out_dir: str):
        self.out_dir = out_dir
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
            
    def generate(self, equity_curve: pd.Series, metrics: dict, run_name: str = "backtest"):
        """
        Generates a tearsheet with charts and metrics.
        """
        logger.info(f"Generating tearsheet for {run_name}...")
        
        # 1. Plot Equity Curve
        plt.figure(figsize=(12, 8))
        
        ax1 = plt.subplot(2, 1, 1)
        equity_curve.plot(ax=ax1, title="Equity Curve")
        ax1.grid(True)
        
        # 2. Plot Drawdown
        ax2 = plt.subplot(2, 1, 2)
        rolling_max = equity_curve.cummax()
        drawdown = (equity_curve - rolling_max) / rolling_max
        drawdown.plot(ax=ax2, title="Drawdown", color='red', fillstyle='bottom')
        ax2.fill_between(drawdown.index, drawdown, color='red', alpha=0.3)
        ax2.grid(True)
        
        plt.tight_layout()
        
        chart_path = os.path.join(self.out_dir, f"{run_name}_chart.png")
        plt.savefig(chart_path)
        plt.close()
        
        # 3. Create Markdown Summary
        md_path = os.path.join(self.out_dir, f"{run_name}_summary.md")
        
        with open(md_path, 'w') as f:
            f.write(f"# Backtest Summary: {run_name}\n\n")
            f.write("## Performance Metrics\n\n")
            f.write("| Metric | Value |\n")
            f.write("|---|---|\n")
            for k, v in metrics.items():
                if isinstance(v, float):
                    f.write(f"| {k} | {v:.4f} |\n")
                else:
                    f.write(f"| {k} | {v} |\n")
            
            f.write("\n## Equity Curve\n\n")
            f.write(f"![Equity Curve]({os.path.basename(chart_path)})\n")
            
        logger.info(f"Tearsheet saved to {md_path}")
