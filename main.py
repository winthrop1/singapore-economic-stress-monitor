#!/usr/bin/env python3
"""
Singapore Economic Stress Monitor - Main Orchestration Script

This script runs the complete stress scoring pipeline:
1. Load economic indicator data (GDP, CPI, Unemployment)
2. Normalize indicators to 0-100 stress scale
3. Calculate weighted composite stress score
4. Generate 4 visualization charts
5. Display summary statistics

Usage:
    python main.py              # Run full pipeline
    python main.py --quiet      # Minimal output
    python main.py --no-charts  # Skip chart generation

Output:
    - Charts saved to output/ directory
    - Summary statistics printed to console

For more details, see README.md and USAGE.md
"""

import sys
import argparse
from datetime import datetime
import pandas as pd

# Import project modules
import config
from src.data_loader import load_all_data, get_summary_stats
from src.normalizer import normalize_all_indicators, get_normalization_summary
from src.stress_scorer import calculate_composite_score, get_stress_summary
from src.visualizer import create_all_charts


def print_header(title: str, width: int = 60):
    """Print a formatted header."""
    print("\n" + "="*width)
    print(title.center(width))
    print("="*width)


def print_section(title: str, width: int = 60):
    """Print a formatted section header."""
    print(f"\n{title}")
    print("-"*width)


def run_dashboard(create_charts: bool = True, verbose: bool = True):
    """
    Run the complete Singapore Economic Stress Monitor pipeline.

    Args:
        create_charts: Whether to generate visualization charts
        verbose: Whether to show detailed progress output

    Returns:
        Dictionary containing:
        - data: Raw indicator data
        - normalized: Normalized indicator data
        - stress_df: Stress scores DataFrame
        - summary: Summary statistics
        - chart_paths: Paths to generated charts (if create_charts=True)
    """
    # Temporarily override verbose setting
    original_verbose = config.VERBOSE
    config.VERBOSE = verbose

    try:
        # =====================================================================
        # STEP 1: LOAD DATA
        # =====================================================================
        if verbose:
            print_header("SINGAPORE ECONOMIC STRESS MONITOR")
            print(f"Run Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"\nConfiguration:")
            print(f"  Indicators: {len(config.DATA_FILES)}")
            print(f"  Weights: GDP {config.INDICATOR_WEIGHTS['gdp']:.0%}, "
                  f"CPI {config.INDICATOR_WEIGHTS['cpi']:.0%}, "
                  f"Unemployment {config.INDICATOR_WEIGHTS['unemployment']:.0%}")
            print(f"  Rolling Window: {config.ROLLING_WINDOW_MONTHS} months")
            print(f"  Alert Thresholds: Green <40, Amber 40-64, Red ≥65")

        data, dates = load_all_data()

        if verbose:
            print_section("DATA LOADED")
            print(f"  Date Range: {dates.min().strftime('%Y-%m')} to {dates.max().strftime('%Y-%m')}")
            print(f"  Total Months: {len(dates)}")

        # =====================================================================
        # STEP 2: NORMALIZE INDICATORS
        # =====================================================================
        normalized = normalize_all_indicators(data)

        if verbose:
            print_section("NORMALIZATION SUMMARY")
            norm_summary = get_normalization_summary(normalized)
            pd.set_option('display.float_format', '{:.1f}'.format)
            print(norm_summary.to_string(index=False))

        # =====================================================================
        # STEP 3: CALCULATE STRESS SCORES
        # =====================================================================
        stress_df = calculate_composite_score(normalized)
        summary = get_stress_summary(stress_df)

        if verbose:
            print_section("STRESS SCORE ANALYSIS")
            print(f"\nOverall Statistics:")
            print(f"  Date Range:  {summary['date_range_start']} to {summary['date_range_end']}")
            print(f"  Valid Months: {summary['total_months']}")
            print(f"  Mean Score:   {summary['mean_score']:.1f}")
            print(f"  Std Dev:      {summary['std_score']:.1f}")
            print(f"  Min Score:    {summary['min_score']:.1f}")
            print(f"  Max Score:    {summary['max_score']:.1f}")

            print(f"\n  Alert Level Distribution:")
            print(f"    🟢 Green (0-39):   {summary['green_count']:3d} months ({summary['green_percent']:5.1f}%)")
            print(f"    🟡 Amber (40-64):  {summary['amber_count']:3d} months ({summary['amber_percent']:5.1f}%)")
            print(f"    🔴 Red (65-100):   {summary['red_count']:3d} months ({summary['red_percent']:5.1f}%)")

            if summary['recent_12m_mean'] is not None:
                trend_symbol = "↑" if summary['recent_vs_historical'] > 0 else "↓"
                trend_word = "ABOVE" if summary['recent_vs_historical'] > 0 else "BELOW"
                print(f"\n  Recent Trend (Last 12 Months):")
                print(f"    Recent Mean:  {summary['recent_12m_mean']:.1f}")
                print(f"    vs Historical: {summary['recent_vs_historical']:+.1f} {trend_symbol} ({trend_word} historical average)")

            print(f"\n  Alert Transitions:")
            print(f"    Total:           {summary['total_transitions']}")
            print(f"    Escalating:      {summary['escalating_transitions']} (stress increasing)")
            print(f"    De-escalating:   {summary['de_escalating_transitions']} (stress decreasing)")

        # =====================================================================
        # STEP 4: CURRENT STATUS (ALWAYS SHOWN)
        # =====================================================================
        alert_emoji = {'Green': '🟢', 'Amber': '🟡', 'Red': '🔴'}
        latest_emoji = alert_emoji.get(summary['latest_alert'], '❓')

        print_header("CURRENT STATUS")
        print(f"\nAs of: {summary['latest_date']}")
        print(f"\n  Composite Stress Score: {summary['latest_score']:.1f}")
        print(f"  Alert Level:            {latest_emoji} {summary['latest_alert'].upper()}")

        # Get component breakdown
        latest_row = stress_df.dropna(subset=['composite_score']).iloc[-1]
        print(f"\n  Component Breakdown:")
        print(f"    GDP Score:          {latest_row['gdp_score']:.1f} → Contributes {config.INDICATOR_WEIGHTS['gdp'] * latest_row['gdp_score']:.1f} points (weight: {config.INDICATOR_WEIGHTS['gdp']:.0%})")
        print(f"    CPI Score:          {latest_row['cpi_score']:.1f} → Contributes {config.INDICATOR_WEIGHTS['cpi'] * latest_row['cpi_score']:.1f} points (weight: {config.INDICATOR_WEIGHTS['cpi']:.0%})")
        print(f"    Unemployment Score: {latest_row['unemployment_score']:.1f} → Contributes {config.INDICATOR_WEIGHTS['unemployment'] * latest_row['unemployment_score']:.1f} points (weight: {config.INDICATOR_WEIGHTS['unemployment']:.0%})")

        # Alert interpretation
        print(f"\n  Alert Interpretation:")
        if summary['latest_alert'] == 'Green':
            print(f"    ✓ Low stress conditions")
            print(f"    ✓ Routine monitoring recommended")
        elif summary['latest_alert'] == 'Amber':
            print(f"    ⚠ Elevated economic stress")
            print(f"    ⚠ Heightened vigilance recommended")
            print(f"    ⚠ Monitor for further deterioration")
        else:  # Red
            print(f"    ⛔ HIGH STRESS CONDITIONS")
            print(f"    ⛔ Activate risk response protocols")
            print(f"    ⛔ Board escalation recommended")

        # =====================================================================
        # STEP 5: CREATE CHARTS (OPTIONAL)
        # =====================================================================
        chart_paths = None
        if create_charts:
            chart_paths = create_all_charts(stress_df, normalized)

            if verbose:
                print_section("CHARTS GENERATED")
                for chart_type, path in chart_paths.items():
                    print(f"  ✓ {chart_type.capitalize():15s}: {path}")

        # =====================================================================
        # COMPLETION
        # =====================================================================
        if verbose:
            print_header("DASHBOARD COMPLETE")
            if create_charts:
                print("✓ All charts saved to output/ directory")
            print("✓ Dashboard execution successful\n")

        # Return results
        return {
            'data': data,
            'normalized': normalized,
            'stress_df': stress_df,
            'summary': summary,
            'chart_paths': chart_paths
        }

    finally:
        # Restore original verbose setting
        config.VERBOSE = original_verbose


def main():
    """Main entry point for command-line execution."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Singapore Economic Stress Monitor - Early-Warning Dashboard',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                # Run full dashboard with charts
  python main.py --quiet        # Minimal output
  python main.py --no-charts    # Skip chart generation

For more information, see README.md and USAGE.md
        """
    )

    parser.add_argument('--quiet', '-q',
                       action='store_true',
                       help='Minimal console output (only show current status)')

    parser.add_argument('--no-charts', '-n',
                       action='store_true',
                       help='Skip chart generation (faster execution)')

    parser.add_argument('--version', '-v',
                       action='version',
                       version='Singapore Economic Stress Monitor v1.0.0')

    args = parser.parse_args()

    # Run dashboard
    try:
        results = run_dashboard(
            create_charts=not args.no_charts,
            verbose=not args.quiet
        )

        # Success
        return 0

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}", file=sys.stderr)
        if config.VERBOSE:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
