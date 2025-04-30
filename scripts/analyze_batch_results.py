#!/usr/bin/env python3
"""
analyze_batch_results.py - Analyze and visualize batch processing results

Usage:
    python analyze_batch_results.py [--metrics batch_metrics.json]
    
Example:
    python analyze_batch_results.py
    python analyze_batch_results.py --metrics custom_metrics.json
"""

import os
import sys
import json
import argparse
from pathlib import Path
import logging
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
import seaborn as sns

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('analyze_results')

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
DEFAULT_METRICS_FILE = OUTPUT_DIR / "batch_metrics.json"
ANALYSIS_DIR = OUTPUT_DIR / "analysis"

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Analyze batch processing results")
    parser.add_argument("--metrics", default=str(DEFAULT_METRICS_FILE),
                        help=f"Path to metrics JSON file (default: {DEFAULT_METRICS_FILE})")
    
    return parser.parse_args()

def load_metrics(file_path):
    """Load metrics from JSON file."""
    try:
        with open(file_path, 'r') as f:
            metrics = json.load(f)
        logger.info(f"Loaded metrics from {file_path}")
        return metrics
    except Exception as e:
        logger.error(f"Error loading metrics file: {e}")
        sys.exit(1)

def create_dataframes(metrics):
    """Create pandas DataFrames from metrics data for analysis."""
    # Create dataframe for issue metrics
    issues_df = pd.DataFrame([
        {
            "date": issue["date"],
            "publication": issue["publication"],
            "total_articles": issue["counts"].get("total_articles", 0),
            "news_articles": issue["counts"].get("news_articles", 0),
            "ad_articles": issue["counts"].get("ad_articles", 0),
            "hsa_ready_articles": issue["counts"].get("hsa_ready_articles", 0),
            "news_percentage": issue["counts"].get("news_articles", 0) / issue["counts"].get("total_articles", 1) * 100,
            "processing_time": issue["timestamps"].get("total", 0),
            "fetch_time": issue["timestamps"].get("fetch", 0),
            "prefilter_time": issue["timestamps"].get("prefilter", 0),
            "classify_time": issue["timestamps"].get("classify", 0)
        }
        for issue in metrics["issues"] if issue
    ])
    
    # Sort by date
    issues_df["date"] = pd.to_datetime(issues_df["date"])
    issues_df = issues_df.sort_values("date")
    
    return issues_df

def plot_article_type_distribution(df, output_dir):
    """Plot the distribution of article types by publication."""
    # Prepare data
    plot_data = df.copy()
    plot_data["ad_percentage"] = 100 - plot_data["news_percentage"]
    
    # Plot
    plt.figure(figsize=(12, 8))
    
    # Create a bar chart
    ax = plt.subplot(111)
    
    # Create the stacked bars
    ax.bar(plot_data["date"], plot_data["news_percentage"], label="News Articles", color="cornflowerblue")
    ax.bar(plot_data["date"], plot_data["ad_percentage"], bottom=plot_data["news_percentage"], label="Ad Articles", color="lightcoral")
    
    # Add labels and title
    plt.title("Article Type Distribution by Publication and Date", fontsize=16)
    plt.xlabel("Date", fontsize=14)
    plt.ylabel("Percentage", fontsize=14)
    plt.ylim(0, 100)
    plt.grid(axis="y", linestyle="--", alpha=0.7)
    
    # Add percentage labels
    for i, (_, row) in enumerate(plot_data.iterrows()):
        plt.text(i, row["news_percentage"] / 2, f"{row['news_percentage']:.1f}%", 
                ha="center", va="center", color="white", fontweight="bold")
        plt.text(i, row["news_percentage"] + row["ad_percentage"] / 2, f"{row['ad_percentage']:.1f}%", 
                ha="center", va="center", color="white", fontweight="bold")
    
    # Add a legend
    plt.legend(loc="upper right")
    
    # Color code publications
    pub_colors = {}
    for i, pub in enumerate(df["publication"].unique()):
        pub_colors[pub] = plt.cm.tab10(i)
    
    # Add publication names with color coding
    for i, (_, row) in enumerate(plot_data.iterrows()):
        plt.annotate(row["publication"], xy=(i, -5), xytext=(i, -5),
                    ha="right", va="center", rotation=45, fontsize=10, 
                    color=pub_colors[row["publication"]])
    
    # Format x-axis
    plt.xticks(range(len(plot_data)), plot_data["date"].dt.strftime("%Y-%m-%d"), rotation=45, ha="right")
    
    # Adjust layout
    plt.tight_layout()
    
    # Save the figure
    output_file = output_dir / "article_type_distribution.png"
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    logger.info(f"Saved article type distribution plot to {output_file}")
    
    # Close the figure
    plt.close()

def plot_processing_time(df, output_dir):
    """Plot processing time breakdown by issue."""
    # Prepare data
    time_columns = ["fetch_time", "prefilter_time", "classify_time"]
    plot_data = df.copy()
    
    # Normalize time to minutes
    for col in time_columns:
        plot_data[col] = plot_data[col] / 60  # Convert seconds to minutes
    
    # Other processing time (total - measured steps)
    plot_data["other_time"] = plot_data["processing_time"] / 60 - plot_data[time_columns].sum(axis=1)
    
    # Plot
    plt.figure(figsize=(12, 8))
    
    # Create a stacked bar chart
    ax = plt.subplot(111)
    
    # Bottom position for stacking
    bottom = [0] * len(plot_data)
    
    # Color map
    colors = ["skyblue", "lightgreen", "coral", "lightgray"]
    labels = ["Fetch", "Pre-filter", "Classification", "Other"]
    
    # Create the stacked bars for each time component
    for i, col in enumerate(time_columns + ["other_time"]):
        ax.bar(range(len(plot_data)), plot_data[col], bottom=bottom, label=labels[i], color=colors[i])
        # Update bottom position for next stack
        bottom = [b + t for b, t in zip(bottom, plot_data[col])]
    
    # Add labels and title
    plt.title("Processing Time Breakdown by Issue", fontsize=16)
    plt.xlabel("Issue", fontsize=14)
    plt.ylabel("Time (minutes)", fontsize=14)
    plt.grid(axis="y", linestyle="--", alpha=0.7)
    
    # Add a legend
    plt.legend(loc="upper right")
    
    # Format x-axis
    plt.xticks(range(len(plot_data)), 
              [f"{d.strftime('%Y-%m-%d')}\n{p}" 
               for d, p in zip(plot_data["date"], plot_data["publication"])], 
              rotation=45, ha="right")
    
    # Add total time labels
    for i, (_, row) in enumerate(plot_data.iterrows()):
        plt.text(i, row["processing_time"]/60 + 0.5, f"{row['processing_time']/60:.1f} min", 
                ha="center", va="bottom", fontsize=9)
    
    # Adjust layout
    plt.tight_layout()
    
    # Save the figure
    output_file = output_dir / "processing_time_breakdown.png"
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    logger.info(f"Saved processing time breakdown plot to {output_file}")
    
    # Close the figure
    plt.close()

def plot_efficiency_comparison(df, output_dir):
    """Plot efficiency comparison (time saved by pre-filter)."""
    # Prepare data
    plot_data = df.copy()
    
    # Estimate time saved (assume 2 seconds per ad article for classification)
    avg_classify_time_per_article = plot_data["classify_time"].sum() / plot_data["news_articles"].sum()
    plot_data["estimated_time_saved"] = plot_data["ad_articles"] * avg_classify_time_per_article
    plot_data["efficiency_gain"] = (plot_data["estimated_time_saved"] / 
                                   (plot_data["processing_time"] + plot_data["estimated_time_saved"])) * 100
    
    # Plot
    plt.figure(figsize=(12, 8))
    
    # Create bar chart
    ax = plt.subplot(111)
    bars = ax.bar(range(len(plot_data)), plot_data["efficiency_gain"], color="mediumseagreen")
    
    # Add labels and title
    plt.title("Estimated Efficiency Gain from Pre-filtering by Issue", fontsize=16)
    plt.xlabel("Issue", fontsize=14)
    plt.ylabel("Efficiency Gain (%)", fontsize=14)
    plt.ylim(0, max(100, plot_data["efficiency_gain"].max() * 1.1))
    plt.grid(axis="y", linestyle="--", alpha=0.7)
    
    # Add percentage labels
    for i, bar in enumerate(bars):
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 1,
                f"{height:.1f}%", ha="center", va="bottom", fontsize=10)
    
    # Format x-axis
    plt.xticks(range(len(plot_data)), 
              [f"{d.strftime('%Y-%m-%d')}\n{p}" 
               for d, p in zip(plot_data["date"], plot_data["publication"])], 
              rotation=45, ha="right")
    
    # Add a horizontal line for average
    avg_efficiency = plot_data["efficiency_gain"].mean()
    plt.axhline(y=avg_efficiency, color="darkred", linestyle="--", alpha=0.7)
    plt.text(len(plot_data)-1, avg_efficiency + 2, f"Average: {avg_efficiency:.1f}%", 
            ha="right", va="bottom", color="darkred")
    
    # Adjust layout
    plt.tight_layout()
    
    # Save the figure
    output_file = output_dir / "efficiency_gain.png"
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    logger.info(f"Saved efficiency gain plot to {output_file}")
    
    # Close the figure
    plt.close()

def generate_summary_report(df, aggregate_data, output_dir):
    """Generate a summary report of the batch processing results."""
    # Calculate overall metrics
    total_articles = df["total_articles"].sum()
    total_news = df["news_articles"].sum()
    total_ads = df["ad_articles"].sum()
    avg_news_pct = (total_news / total_articles) * 100 if total_articles > 0 else 0
    
    # Publication-specific metrics
    pub_metrics = df.groupby("publication").agg({
        "total_articles": "sum",
        "news_articles": "sum",
        "ad_articles": "sum",
        "processing_time": "sum"
    }).reset_index()
    
    pub_metrics["news_percentage"] = (pub_metrics["news_articles"] / pub_metrics["total_articles"]) * 100
    pub_metrics["avg_time_per_article"] = pub_metrics["processing_time"] / pub_metrics["total_articles"]
    
    # Time period analysis
    df_sorted = df.sort_values("date")
    decade_metrics = df.copy()
    decade_metrics["decade"] = decade_metrics["date"].dt.year // 10 * 10
    decade_metrics = decade_metrics.groupby("decade").agg({
        "total_articles": "sum",
        "news_articles": "sum",
        "ad_articles": "sum"
    }).reset_index()
    
    decade_metrics["news_percentage"] = (decade_metrics["news_articles"] / decade_metrics["total_articles"]) * 100
    
    # Generate the report
    report = f"""# StoryDredge Batch Processing Results Summary
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Overview
- **Total Issues Processed:** {len(df)}
- **Total Articles:** {total_articles}
- **News Articles:** {total_news} ({avg_news_pct:.1f}%)
- **Ad Articles:** {total_ads} ({100-avg_news_pct:.1f}%)
- **Total Processing Time:** {df["processing_time"].sum()/60:.1f} minutes

## Publication Analysis
| Publication | Total Articles | News Articles | News % | Processing Time (min) |
|-------------|----------------|---------------|--------|------------------------|
"""
    
    # Add publication rows
    for _, row in pub_metrics.iterrows():
        report += f"| {row['publication']} | {row['total_articles']} | {row['news_articles']} | {row['news_percentage']:.1f}% | {row['processing_time']/60:.1f} |\n"
    
    # Add decade analysis
    report += """
## Decade Analysis
| Decade | Total Articles | News Articles | News % |
|--------|----------------|---------------|--------|
"""
    
    # Add decade rows
    for _, row in decade_metrics.iterrows():
        report += f"| {row['decade']}s | {row['total_articles']} | {row['news_articles']} | {row['news_percentage']:.1f}% |\n"
    
    # Ad detection effectiveness
    report += f"""
## Pre-filter Effectiveness
- **Average News Content:** {avg_news_pct:.1f}%
- **Average Ads Detected:** {100-avg_news_pct:.1f}%
- **Estimated Average Time Saved:** {df["estimated_time_saved"].mean()/60:.1f} minutes per issue
- **Average Efficiency Gain:** {df["efficiency_gain"].mean():.1f}%

## Key Findings
1. The pre-filter identified an average of {100-avg_news_pct:.1f}% of content as advertisements across all publications.
2. The most ad-heavy publication was {pub_metrics.loc[pub_metrics['news_percentage'].idxmin(), 'publication']} with only {pub_metrics['news_percentage'].min():.1f}% news content.
3. The most news-focused publication was {pub_metrics.loc[pub_metrics['news_percentage'].idxmax(), 'publication']} with {pub_metrics['news_percentage'].max():.1f}% news content.
4. Processing time was reduced by approximately {df["efficiency_gain"].mean():.1f}% through the pre-filtering step.
"""
    
    # Save the report
    report_file = output_dir / "batch_processing_summary.md"
    with open(report_file, "w") as f:
        f.write(report)
    
    logger.info(f"Saved summary report to {report_file}")

def main():
    """Main function."""
    args = parse_arguments()
    
    # Create output directory
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Load metrics
    metrics = load_metrics(args.metrics)
    
    # Create dataframes
    issues_df = create_dataframes(metrics)
    
    # Generate plots
    plot_article_type_distribution(issues_df, ANALYSIS_DIR)
    plot_processing_time(issues_df, ANALYSIS_DIR)
    plot_efficiency_comparison(issues_df, ANALYSIS_DIR)
    
    # Generate summary report
    generate_summary_report(issues_df, metrics["aggregate"], ANALYSIS_DIR)
    
    logger.info(f"Analysis complete. Results saved to {ANALYSIS_DIR}")
    logger.info(f"Summary report: {ANALYSIS_DIR / 'batch_processing_summary.md'}")

if __name__ == "__main__":
    main() 