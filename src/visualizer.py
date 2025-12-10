"""
Visualizer Module

This module creates 4 publication-ready charts for the Singapore Economic Stress Monitor:

1. Stress Timeseries: Line chart with Green/Amber/Red threshold bands
2. Component Breakdown: Stacked area showing indicator contributions
3. Correlation Heatmap: 3×3 matrix showing indicator correlations
4. Alert Timeline: Horizontal color-coded bars showing stress regimes

All charts use a consistent color scheme:
- Green: #2ecc71 (low stress)
- Amber: #f39c12 (elevated stress)
- Red: #e74c3c (high stress)

Charts are saved to output/ directory as PNG files.
"""

import os
from typing import Dict, Optional

import numpy as np
import pandas as pd

import config


def _prepare_matplotlib_environment():
    """Ensure Matplotlib can write cache/config files inside the project."""
    safe_base = os.path.join(config.OUTPUT_DIR, '.matplotlib_cache')
    os.makedirs(safe_base, exist_ok=True)

    mpl_config_dir = os.environ.get('MPLCONFIGDIR')
    if not mpl_config_dir or not os.access(mpl_config_dir, os.W_OK):
        mpl_config_dir = safe_base
        os.environ['MPLCONFIGDIR'] = mpl_config_dir

    cache_dir = os.environ.get('XDG_CACHE_HOME')
    if not cache_dir or not os.access(cache_dir, os.W_OK):
        cache_dir = os.path.join(safe_base, 'cache')
        os.environ['XDG_CACHE_HOME'] = cache_dir

    os.makedirs(cache_dir, exist_ok=True)
    fontconfig_dir = os.path.join(cache_dir, 'fontconfig')
    os.makedirs(fontconfig_dir, exist_ok=True)


_prepare_matplotlib_environment()

import matplotlib  # noqa: E402

if not os.environ.get('MPLBACKEND'):
    matplotlib.use('Agg')

import matplotlib.patches as mpatches  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402


def setup_chart_style():
    """
    Configure matplotlib style for professional-looking charts.

    Sets up:
    - Font sizes for readability
    - Grid style for clarity
    - Figure background color
    - Default line widths
    """
    plt.style.use('seaborn-v0_8-darkgrid')
    plt.rcParams['figure.facecolor'] = 'white'
    plt.rcParams['axes.facecolor'] = '#f8f9fa'
    plt.rcParams['axes.grid'] = True
    plt.rcParams['grid.alpha'] = 0.3
    plt.rcParams['font.size'] = 10
    plt.rcParams['axes.titlesize'] = 14
    plt.rcParams['axes.labelsize'] = 11
    plt.rcParams['xtick.labelsize'] = 9
    plt.rcParams['ytick.labelsize'] = 9
    plt.rcParams['legend.fontsize'] = 9


def plot_stress_timeseries(stress_df: pd.DataFrame, output_path: Optional[str] = None) -> str:
    """
    Create line chart of composite stress score over time with threshold bands.

    The chart shows:
    - Black line: Composite stress score
    - Green band: 0-39 (low stress zone)
    - Amber band: 40-64 (elevated stress zone)
    - Red band: 65-100 (high stress zone)
    - Horizontal threshold lines at 40 and 65

    Args:
        stress_df: DataFrame with 'composite_score' column and date index
        output_path: Where to save chart (default: from config)

    Returns:
        Path to saved chart file

    Example:
        >>> path = plot_stress_timeseries(stress_df)
        >>> print(f"Chart saved to {path}")
    """
    setup_chart_style()

    if output_path is None:
        output_path = config.CHART_FILES['timeseries']

    # Filter to valid scores
    valid_df = stress_df.dropna(subset=['composite_score'])

    if len(valid_df) == 0:
        raise ValueError("No valid stress scores to plot")

    # Create figure
    fig, ax = plt.subplots(figsize=config.CHART_SIZE)

    # Draw threshold bands (background)
    ax.axhspan(0, 40, facecolor=config.THRESHOLD_COLORS['green'], alpha=0.15, zorder=0)
    ax.axhspan(40, 65, facecolor=config.THRESHOLD_COLORS['amber'], alpha=0.15, zorder=0)
    ax.axhspan(65, 100, facecolor=config.THRESHOLD_COLORS['red'], alpha=0.15, zorder=0)

    # Draw threshold lines
    ax.axhline(y=40, color=config.THRESHOLD_COLORS['amber'], linestyle='--',
               linewidth=1.5, alpha=0.6, label='Amber Threshold (40)')
    ax.axhline(y=65, color=config.THRESHOLD_COLORS['red'], linestyle='--',
               linewidth=1.5, alpha=0.6, label='Red Threshold (65)')

    # Plot composite stress score
    ax.plot(valid_df.index, valid_df['composite_score'],
            color='black', linewidth=2, label='Composite Stress Score', zorder=5)

    # Add labels and title
    ax.set_xlabel('Date', fontweight='bold')
    ax.set_ylabel('Stress Score (0-100)', fontweight='bold')
    ax.set_title('Singapore Economic Stress Score - Time Series\n' +
                 f'{valid_df.index.min().strftime("%Y-%m")} to {valid_df.index.max().strftime("%Y-%m")}',
                 fontweight='bold', pad=20)

    # Set y-axis limits
    ax.set_ylim(0, 100)

    # Add legend
    ax.legend(loc='upper left', framealpha=0.9)

    # Add grid
    ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5)

    # Rotate x-axis labels for readability
    plt.xticks(rotation=45, ha='right')

    # Add current status annotation (latest value)
    latest_score = valid_df['composite_score'].iloc[-1]
    latest_date = valid_df.index[-1]
    latest_alert = valid_df['alert_level'].iloc[-1] if 'alert_level' in valid_df.columns else 'Unknown'

    ax.annotate(f'Latest: {latest_score:.1f}\n({latest_alert})',
                xy=(latest_date, latest_score),
                xytext=(20, 20), textcoords='offset points',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor='gray', alpha=0.9),
                arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0', color='gray'),
                fontsize=9, fontweight='bold')

    # Tight layout
    plt.tight_layout()

    # Save chart
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=config.CHART_DPI, bbox_inches='tight')
    plt.close()

    if config.VERBOSE:
        print(f"  ✓ Saved timeseries chart to {output_path}")

    return output_path


def plot_component_breakdown(stress_df: pd.DataFrame, output_path: Optional[str] = None) -> str:
    """
    Create stacked area chart showing weighted contributions of each indicator.

    The chart shows:
    - GDP contribution (bottom, blue)
    - CPI contribution (middle, orange)
    - Unemployment contribution (top, green)
    - Each contribution = weight × normalized_score

    Args:
        stress_df: DataFrame with component score columns
        output_path: Where to save chart (default: from config)

    Returns:
        Path to saved chart file

    Example:
        >>> path = plot_component_breakdown(stress_df)
    """
    setup_chart_style()

    if output_path is None:
        output_path = config.CHART_FILES['components']

    # Filter to valid scores
    valid_df = stress_df.dropna(subset=['composite_score'])

    if len(valid_df) == 0:
        raise ValueError("No valid stress scores to plot")

    # Calculate weighted contributions
    contributions = pd.DataFrame(index=valid_df.index)

    for indicator_name, weight in config.INDICATOR_WEIGHTS.items():
        score_column = f'{indicator_name}_score'
        contributions[indicator_name] = weight * valid_df[score_column]

    # Create figure
    fig, ax = plt.subplots(figsize=config.CHART_SIZE)

    # Define colors for each indicator
    indicator_colors = {
        'gdp': '#3498db',         # Blue
        'cpi': '#e67e22',         # Orange
        'unemployment': '#27ae60' # Green
    }

    # Create stacked area chart
    indicators = list(config.INDICATOR_WEIGHTS.keys())
    colors = [indicator_colors[ind] for ind in indicators]

    ax.stackplot(contributions.index,
                 *[contributions[ind] for ind in indicators],
                 labels=[f'{ind.upper()} ({config.INDICATOR_WEIGHTS[ind]:.0%})' for ind in indicators],
                 colors=colors,
                 alpha=0.7)

    # Add composite score line on top
    ax.plot(valid_df.index, valid_df['composite_score'],
            color='black', linewidth=2, linestyle='--',
            label='Composite Score', zorder=5, alpha=0.8)

    # Add labels and title
    ax.set_xlabel('Date', fontweight='bold')
    ax.set_ylabel('Weighted Contribution to Stress Score', fontweight='bold')
    ax.set_title('Singapore Economic Stress Score - Component Breakdown\n' +
                 f'{valid_df.index.min().strftime("%Y-%m")} to {valid_df.index.max().strftime("%Y-%m")}',
                 fontweight='bold', pad=20)

    # Set y-axis limits
    ax.set_ylim(0, 100)

    # Add legend
    ax.legend(loc='upper left', framealpha=0.9)

    # Add grid
    ax.grid(True, alpha=0.3, linestyle='-', linewidth=0.5, axis='y')

    # Rotate x-axis labels
    plt.xticks(rotation=45, ha='right')

    # Tight layout
    plt.tight_layout()

    # Save chart
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=config.CHART_DPI, bbox_inches='tight')
    plt.close()

    if config.VERBOSE:
        print(f"  ✓ Saved component breakdown chart to {output_path}")

    return output_path


def plot_correlation_heatmap(normalized_data: Dict[str, pd.DataFrame],
                             output_path: Optional[str] = None) -> str:
    """
    Create correlation heatmap showing relationships between indicators.

    The heatmap shows:
    - 3×3 matrix of correlations
    - Correlation coefficients annotated in each cell
    - Color intensity shows strength of correlation

    Args:
        normalized_data: Dictionary of {indicator_name: DataFrame with 'normalized' column}
        output_path: Where to save chart (default: from config)

    Returns:
        Path to saved chart file

    Example:
        >>> path = plot_correlation_heatmap(normalized_data)
    """
    setup_chart_style()

    if output_path is None:
        output_path = config.CHART_FILES['heatmap']

    # Extract normalized scores for each indicator
    scores_df = pd.DataFrame()

    for indicator_name in config.INDICATOR_WEIGHTS.keys():
        scores_df[indicator_name.upper()] = normalized_data[indicator_name]['normalized']

    # Calculate correlation matrix
    corr_matrix = scores_df.corr()

    # Create figure
    fig, ax = plt.subplots(figsize=(8, 7))

    # Create heatmap
    im = ax.imshow(corr_matrix, cmap='RdYlGn_r', aspect='auto',
                   vmin=-1, vmax=1, alpha=0.8)

    # Add colorbar
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Correlation Coefficient', rotation=270, labelpad=20, fontweight='bold')

    # Set ticks and labels
    indicators = list(corr_matrix.columns)
    ax.set_xticks(range(len(indicators)))
    ax.set_yticks(range(len(indicators)))
    ax.set_xticklabels(indicators, fontweight='bold')
    ax.set_yticklabels(indicators, fontweight='bold')

    # Rotate x-axis labels
    plt.setp(ax.get_xticklabels(), rotation=45, ha='right', rotation_mode='anchor')

    # Annotate cells with correlation values
    for i in range(len(indicators)):
        for j in range(len(indicators)):
            value = corr_matrix.iloc[i, j]
            color = 'white' if abs(value) > 0.5 else 'black'
            ax.text(j, i, f'{value:.2f}',
                   ha='center', va='center', color=color, fontweight='bold', fontsize=11)

    # Add title
    ax.set_title('Correlation Matrix - Economic Indicators\n(Normalized Stress Scores)',
                 fontweight='bold', pad=20)

    # Tight layout
    plt.tight_layout()

    # Save chart
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=config.CHART_DPI, bbox_inches='tight')
    plt.close()

    if config.VERBOSE:
        print(f"  ✓ Saved correlation heatmap to {output_path}")

    return output_path


def plot_alert_timeline(stress_df: pd.DataFrame, output_path: Optional[str] = None) -> str:
    """
    Create horizontal timeline showing Green/Amber/Red alert periods.

    The chart shows:
    - Horizontal bars colored by alert level
    - Clear visual of stress regime changes over time
    - Summary statistics (% time in each alert level)

    Args:
        stress_df: DataFrame with 'alert_level' column and date index
        output_path: Where to save chart (default: from config)

    Returns:
        Path to saved chart file

    Example:
        >>> path = plot_alert_timeline(stress_df)
    """
    setup_chart_style()

    if output_path is None:
        output_path = config.CHART_FILES['alerts']

    # Filter to valid scores
    valid_df = stress_df.dropna(subset=['composite_score'])

    if len(valid_df) == 0:
        raise ValueError("No valid stress scores to plot")

    # Create figure with two subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(config.CHART_SIZE[0], config.CHART_SIZE[1] + 2),
                                   gridspec_kw={'height_ratios': [3, 1]})

    # --- Top panel: Timeline bar chart ---

    # Map alert levels to colors
    alert_colors = {
        'Green': config.THRESHOLD_COLORS['green'],
        'Amber': config.THRESHOLD_COLORS['amber'],
        'Red': config.THRESHOLD_COLORS['red'],
        'Unknown': '#95a5a6'  # Gray for unknown
    }

    # Create color array for bars
    colors = [alert_colors.get(level, '#95a5a6') for level in valid_df['alert_level']]

    # Plot horizontal bars
    ax1.bar(valid_df.index, height=1, width=30, color=colors,
           edgecolor='none', align='edge')

    # Add labels and title
    ax1.set_xlabel('Date', fontweight='bold')
    ax1.set_ylabel('Alert Level', fontweight='bold')
    ax1.set_title('Singapore Economic Stress Alert Timeline\n' +
                  f'{valid_df.index.min().strftime("%Y-%m")} to {valid_df.index.max().strftime("%Y-%m")}',
                  fontweight='bold', pad=20)

    # Set y-axis
    ax1.set_ylim(0, 1)
    ax1.set_yticks([0.5])
    ax1.set_yticklabels(['Alert Status'])

    # Add legend
    legend_patches = [
        mpatches.Patch(color=config.THRESHOLD_COLORS['green'], label='Green (0-39)'),
        mpatches.Patch(color=config.THRESHOLD_COLORS['amber'], label='Amber (40-64)'),
        mpatches.Patch(color=config.THRESHOLD_COLORS['red'], label='Red (65-100)')
    ]
    ax1.legend(handles=legend_patches, loc='upper left', framealpha=0.9, ncol=3)

    # Remove top and right spines
    ax1.spines['top'].set_visible(False)
    ax1.spines['right'].set_visible(False)
    ax1.spines['left'].set_visible(False)

    # Rotate x-axis labels
    plt.setp(ax1.get_xticklabels(), rotation=45, ha='right')

    # --- Bottom panel: Distribution bar chart ---

    # Calculate alert distribution
    alert_counts = valid_df['alert_level'].value_counts()
    total = len(valid_df)

    distribution = []
    for level in ['Green', 'Amber', 'Red']:
        count = alert_counts.get(level, 0)
        pct = 100 * count / total if total > 0 else 0
        distribution.append({'level': level, 'count': count, 'percent': pct})

    dist_df = pd.DataFrame(distribution)

    # Plot distribution
    bars = ax2.barh(dist_df['level'], dist_df['percent'],
                    color=[alert_colors[level] for level in dist_df['level']],
                    edgecolor='black', linewidth=1)

    # Add percentage labels on bars
    for i, (bar, row) in enumerate(zip(bars, distribution)):
        width = bar.get_width()
        ax2.text(width + 1, bar.get_y() + bar.get_height()/2,
                f'{row["count"]} months ({row["percent"]:.1f}%)',
                ha='left', va='center', fontweight='bold', fontsize=9)

    # Add labels
    ax2.set_xlabel('Percentage of Time (%)', fontweight='bold')
    ax2.set_ylabel('Alert Level', fontweight='bold')
    ax2.set_title('Alert Level Distribution', fontweight='bold', pad=10)
    ax2.set_xlim(0, 100)

    # Add grid
    ax2.grid(True, alpha=0.3, axis='x')

    # Remove top and right spines
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)

    # Tight layout
    plt.tight_layout()

    # Save chart
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=config.CHART_DPI, bbox_inches='tight')
    plt.close()

    if config.VERBOSE:
        print(f"  ✓ Saved alert timeline chart to {output_path}")

    return output_path


def create_all_charts(stress_df: pd.DataFrame,
                     normalized_data: Dict[str, pd.DataFrame]) -> Dict[str, str]:
    """
    Create all 4 dashboard charts at once.

    This is a convenience function that generates:
    1. Stress timeseries
    2. Component breakdown
    3. Correlation heatmap
    4. Alert timeline

    Args:
        stress_df: DataFrame with composite scores and alert levels
        normalized_data: Dictionary of normalized indicator DataFrames

    Returns:
        Dictionary mapping chart type to saved file path

    Example:
        >>> paths = create_all_charts(stress_df, normalized_data)
        >>> print(f"Created {len(paths)} charts")
    """
    if config.VERBOSE:
        print("\n" + "="*60)
        print("CREATING VISUALIZATION CHARTS")
        print("="*60)

    chart_paths = {}

    # Chart 1: Timeseries
    if config.VERBOSE:
        print("\nGenerating charts...")
    chart_paths['timeseries'] = plot_stress_timeseries(stress_df)

    # Chart 2: Component breakdown
    chart_paths['components'] = plot_component_breakdown(stress_df)

    # Chart 3: Correlation heatmap
    chart_paths['heatmap'] = plot_correlation_heatmap(normalized_data)

    # Chart 4: Alert timeline
    chart_paths['alerts'] = plot_alert_timeline(stress_df)

    if config.VERBOSE:
        print("\n" + "="*60)
        print("VISUALIZATION COMPLETE")
        print("="*60)
        print(f"✓ Created {len(chart_paths)} charts in output/ directory\n")

    return chart_paths


# =============================================================================
# TESTING / DEMO
# =============================================================================

if __name__ == "__main__":
    """
    Test the visualizer by creating all 4 charts.

    Run this with:
        python -m src.visualizer
    """
    from src.data_loader import load_all_data
    from src.normalizer import normalize_all_indicators
    from src.stress_scorer import calculate_composite_score

    print("\n" + "="*60)
    print("VISUALIZER TEST")
    print("="*60)

    # Load and process data
    print("\nLoading data...")
    data, dates = load_all_data()

    print("\nNormalizing indicators...")
    normalized = normalize_all_indicators(data)

    print("\nCalculating stress scores...")
    stress_df = calculate_composite_score(normalized)

    # Create all charts
    chart_paths = create_all_charts(stress_df, normalized)

    # Show what was created
    print("\nCHARTS CREATED:")
    print("="*60)
    for chart_type, path in chart_paths.items():
        print(f"  {chart_type.capitalize():15s}: {path}")

    print("\n✓ Visualizer test complete!")
    print("\nYou can now view the charts in the output/ directory.")
