"""
Stress Scorer Module

This module calculates the composite economic stress score by combining
normalized indicator scores using weighted averaging.

Process:
1. Take normalized indicators (0-100 scale from normalizer.py)
2. Apply weights (GDP: 35%, CPI: 35%, Unemployment: 30%)
3. Calculate weighted composite score
4. Classify into alert levels (Green/Amber/Red)
5. Detect transitions between alert levels

Why weighted scoring?
- Different indicators have different importance for economic risk
- GDP: Overall economic health (highest weight)
- CPI: Inflation erodes purchasing power (high weight)
- Unemployment: Direct impact on economic participation (medium weight)

Mathematical Details:
    Composite Score = Σ(weight_i × normalized_score_i)

    where:
    - weight_gdp = 0.35
    - weight_cpi = 0.35
    - weight_unemployment = 0.30

    Alert Classification:
    - Green (0-39): Low stress, routine monitoring
    - Amber (40-64): Elevated stress, heightened vigilance
    - Red (65-100): High stress, activate risk response
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, List
import config


def calculate_composite_score(normalized_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Calculate composite stress score from normalized indicators.

    This combines all 3 indicators using weighted averaging:
    - GDP: 35% weight
    - CPI: 35% weight
    - Unemployment: 30% weight

    Args:
        normalized_data: Dictionary of {indicator_name: DataFrame}
                        Each DataFrame has 'normalized' column (0-100 scale)

    Returns:
        DataFrame with columns:
        - 'gdp_score': GDP component (0-100)
        - 'cpi_score': CPI component (0-100)
        - 'unemployment_score': Unemployment component (0-100)
        - 'composite_score': Weighted average (0-100)
        - 'alert_level': Green/Amber/Red classification

    Example:
        >>> normalized = normalize_all_indicators(data)
        >>> stress_df = calculate_composite_score(normalized)
        >>> print(stress_df['composite_score'].tail())
    """
    # Verify we have all required indicators
    required_indicators = set(config.INDICATOR_WEIGHTS.keys())
    available_indicators = set(normalized_data.keys())

    missing = required_indicators - available_indicators
    if missing:
        raise ValueError(f"Missing required indicators: {missing}")

    # Extract normalized scores for each indicator
    # Use the common date index (all indicators already aligned)
    common_index = normalized_data[list(normalized_data.keys())[0]].index

    # Create result DataFrame
    result = pd.DataFrame(index=common_index)

    # Extract component scores
    for indicator_name in config.INDICATOR_WEIGHTS.keys():
        score_column = f'{indicator_name}_score'
        result[score_column] = normalized_data[indicator_name]['normalized']

    # Calculate weighted composite score
    # composite = (w_gdp × gdp_score) + (w_cpi × cpi_score) + (w_unemp × unemp_score)
    result['composite_score'] = 0.0

    for indicator_name, weight in config.INDICATOR_WEIGHTS.items():
        score_column = f'{indicator_name}_score'
        result['composite_score'] += weight * result[score_column]

    # Classify alert level for each month
    result['alert_level'] = result['composite_score'].apply(classify_alert_level)

    # Count how many valid scores we have
    valid_count = result['composite_score'].notna().sum()

    if config.VERBOSE:
        print(f"\n  Computed {valid_count}/{len(result)} composite stress scores")
        if valid_count > 0:
            print(f"  Mean score: {result['composite_score'].mean():.1f}")
            print(f"  Range: {result['composite_score'].min():.1f} - {result['composite_score'].max():.1f}")

    return result


def classify_alert_level(score: float) -> str:
    """
    Classify a stress score into Green/Amber/Red alert level.

    Thresholds (from config):
    - Green (0-39): Low stress, routine monitoring
    - Amber (40-64): Elevated stress, heightened vigilance
    - Red (65-100): High stress, activate risk response protocols

    Note: Boundaries are inclusive on both ends.
    Scores like 64.5 are rounded down to Amber (not Red).

    Args:
        score: Composite stress score (0-100)

    Returns:
        Alert level string: 'Green', 'Amber', or 'Red'

    Examples:
        >>> classify_alert_level(25.0)
        'Green'
        >>> classify_alert_level(52.3)
        'Amber'
        >>> classify_alert_level(64.9)
        'Amber'
        >>> classify_alert_level(65.0)
        'Red'
        >>> classify_alert_level(78.1)
        'Red'
    """
    if pd.isna(score):
        return 'Unknown'

    # Use < instead of <= for upper bounds to handle decimals correctly
    # Green: 0 to < 40
    # Amber: 40 to < 65
    # Red: 65 to 100
    if score < 40:
        return 'Green'
    elif score < 65:
        return 'Amber'
    else:
        return 'Red'


def detect_alert_transitions(stress_df: pd.DataFrame) -> pd.DataFrame:
    """
    Detect transitions between alert levels (regime changes).

    A transition occurs when alert level changes from one month to the next:
    - Green → Amber (stress rising)
    - Amber → Red (crisis developing)
    - Red → Amber (stress easing)
    - Amber → Green (returning to normal)

    Args:
        stress_df: DataFrame with 'alert_level' column

    Returns:
        DataFrame of transitions with columns:
        - 'date': When transition occurred
        - 'from_level': Previous alert level
        - 'to_level': New alert level
        - 'score': Composite score at transition
        - 'direction': 'escalating' or 'de-escalating'

    Example:
        >>> transitions = detect_alert_transitions(stress_df)
        >>> print(f"Found {len(transitions)} alert transitions")
    """
    # Find where alert level changes
    transitions = []

    # Get valid (non-NaN) rows
    valid_df = stress_df.dropna(subset=['composite_score'])

    for i in range(1, len(valid_df)):
        prev_level = valid_df['alert_level'].iloc[i-1]
        curr_level = valid_df['alert_level'].iloc[i]

        if prev_level != curr_level and prev_level != 'Unknown' and curr_level != 'Unknown':
            # Determine direction
            level_order = {'Green': 0, 'Amber': 1, 'Red': 2}
            direction = 'escalating' if level_order[curr_level] > level_order[prev_level] else 'de-escalating'

            transitions.append({
                'date': valid_df.index[i],
                'from_level': prev_level,
                'to_level': curr_level,
                'score': valid_df['composite_score'].iloc[i],
                'direction': direction
            })

    return pd.DataFrame(transitions)


def get_stress_summary(stress_df: pd.DataFrame) -> Dict:
    """
    Get summary statistics for stress scores and alert levels.

    Calculates:
    - Overall statistics (mean, min, max, latest)
    - Alert level distribution (% time in each level)
    - Recent trend (last 12 months average)
    - Number of transitions

    Args:
        stress_df: DataFrame with composite scores and alert levels

    Returns:
        Dictionary with summary statistics

    Example:
        >>> summary = get_stress_summary(stress_df)
        >>> print(f"Latest score: {summary['latest_score']:.1f}")
        >>> print(f"Alert level: {summary['latest_alert']}")
    """
    # Filter to valid scores only
    valid_df = stress_df.dropna(subset=['composite_score'])

    if len(valid_df) == 0:
        return {'error': 'No valid scores available'}

    # Overall statistics
    summary = {
        'total_months': len(valid_df),
        'date_range_start': valid_df.index.min().strftime(config.DATE_FORMAT),
        'date_range_end': valid_df.index.max().strftime(config.DATE_FORMAT),
        'mean_score': valid_df['composite_score'].mean(),
        'min_score': valid_df['composite_score'].min(),
        'max_score': valid_df['composite_score'].max(),
        'std_score': valid_df['composite_score'].std(),
        'latest_score': valid_df['composite_score'].iloc[-1],
        'latest_alert': valid_df['alert_level'].iloc[-1],
        'latest_date': valid_df.index[-1].strftime(config.DATE_FORMAT)
    }

    # Alert level distribution
    alert_counts = valid_df['alert_level'].value_counts()
    total = len(valid_df)

    for level in ['Green', 'Amber', 'Red']:
        count = alert_counts.get(level, 0)
        summary[f'{level.lower()}_count'] = count
        summary[f'{level.lower()}_percent'] = 100 * count / total if total > 0 else 0

    # Recent trend (last 12 months)
    if len(valid_df) >= 12:
        recent_mean = valid_df['composite_score'].iloc[-12:].mean()
        overall_mean = valid_df['composite_score'].mean()
        summary['recent_12m_mean'] = recent_mean
        summary['recent_vs_historical'] = recent_mean - overall_mean
    else:
        summary['recent_12m_mean'] = None
        summary['recent_vs_historical'] = None

    # Transitions
    transitions = detect_alert_transitions(stress_df)
    summary['total_transitions'] = len(transitions)

    if len(transitions) > 0:
        summary['escalating_transitions'] = len(transitions[transitions['direction'] == 'escalating'])
        summary['de_escalating_transitions'] = len(transitions[transitions['direction'] == 'de-escalating'])
    else:
        summary['escalating_transitions'] = 0
        summary['de_escalating_transitions'] = 0

    return summary


def get_component_contributions(stress_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate weighted contributions of each indicator to composite score.

    Shows how much each indicator contributes to the final stress score,
    accounting for both the normalized value and the weight.

    Args:
        stress_df: DataFrame with component scores

    Returns:
        DataFrame with weighted contribution columns:
        - 'gdp_contribution': GDP's weighted contribution
        - 'cpi_contribution': CPI's weighted contribution
        - 'unemployment_contribution': Unemployment's weighted contribution

    Example:
        >>> contributions = get_component_contributions(stress_df)
        >>> print(contributions[['gdp_contribution', 'cpi_contribution', 'unemployment_contribution']].tail())
    """
    result = pd.DataFrame(index=stress_df.index)

    for indicator_name, weight in config.INDICATOR_WEIGHTS.items():
        score_column = f'{indicator_name}_score'
        contribution_column = f'{indicator_name}_contribution'

        # Weighted contribution = weight × normalized_score
        result[contribution_column] = weight * stress_df[score_column]

    return result


# =============================================================================
# TESTING / DEMO
# =============================================================================

if __name__ == "__main__":
    """
    Test the stress scorer by calculating composite scores from normalized data.

    Run this with:
        python -m src.stress_scorer
    """
    from src.data_loader import load_all_data
    from src.normalizer import normalize_all_indicators

    print("\n" + "="*60)
    print("STRESS SCORER TEST")
    print("="*60)

    # Load and normalize data
    print("\nLoading data...")
    data, dates = load_all_data()

    print("\nNormalizing indicators...")
    normalized = normalize_all_indicators(data)

    # Calculate composite stress scores
    print("\n" + "="*60)
    print("CALCULATING COMPOSITE STRESS SCORES")
    print("="*60)

    stress_df = calculate_composite_score(normalized)

    # Show summary statistics
    print("\nSTRESS SCORE SUMMARY:")
    print("="*60)
    summary = get_stress_summary(stress_df)

    print(f"\nDate Range: {summary['date_range_start']} to {summary['date_range_end']}")
    print(f"Total Months: {summary['total_months']}")
    print(f"\nOverall Statistics:")
    print(f"  Mean Score:   {summary['mean_score']:.1f}")
    print(f"  Std Dev:      {summary['std_score']:.1f}")
    print(f"  Min Score:    {summary['min_score']:.1f}")
    print(f"  Max Score:    {summary['max_score']:.1f}")

    print(f"\nAlert Level Distribution:")
    print(f"  🟢 Green (0-39):   {summary['green_count']:3d} months ({summary['green_percent']:5.1f}%)")
    print(f"  🟡 Amber (40-64):  {summary['amber_count']:3d} months ({summary['amber_percent']:5.1f}%)")
    print(f"  🔴 Red (65-100):   {summary['red_count']:3d} months ({summary['red_percent']:5.1f}%)")

    if summary['recent_12m_mean'] is not None:
        trend_symbol = "↑" if summary['recent_vs_historical'] > 0 else "↓"
        print(f"\nRecent Trend (Last 12 Months):")
        print(f"  Recent Mean:  {summary['recent_12m_mean']:.1f}")
        print(f"  vs Historical: {summary['recent_vs_historical']:+.1f} {trend_symbol}")

    print(f"\nLatest Status ({summary['latest_date']}):")

    # Determine emoji for latest alert
    alert_emoji = {'Green': '🟢', 'Amber': '🟡', 'Red': '🔴'}
    latest_emoji = alert_emoji.get(summary['latest_alert'], '❓')

    print(f"  Composite Score: {summary['latest_score']:.1f}")
    print(f"  Alert Level:     {latest_emoji} {summary['latest_alert'].upper()}")

    # Show component breakdown for latest month
    latest_row = stress_df.dropna(subset=['composite_score']).iloc[-1]
    print(f"\n  Component Breakdown:")
    print(f"    GDP:          {latest_row['gdp_score']:.1f} (weight: {config.INDICATOR_WEIGHTS['gdp']:.0%})")
    print(f"    CPI:          {latest_row['cpi_score']:.1f} (weight: {config.INDICATOR_WEIGHTS['cpi']:.0%})")
    print(f"    Unemployment: {latest_row['unemployment_score']:.1f} (weight: {config.INDICATOR_WEIGHTS['unemployment']:.0%})")

    # Show alert transitions
    print(f"\nAlert Transitions:")
    print(f"  Total transitions: {summary['total_transitions']}")
    print(f"    Escalating:      {summary['escalating_transitions']} (stress increasing)")
    print(f"    De-escalating:   {summary['de_escalating_transitions']} (stress decreasing)")

    transitions = detect_alert_transitions(stress_df)
    if len(transitions) > 0:
        print(f"\n  Recent Transitions (Last 5):")
        print("  " + "-"*56)
        recent_transitions = transitions.tail(5)
        for _, trans in recent_transitions.iterrows():
            date_str = trans['date'].strftime('%Y-%m')
            from_emoji = alert_emoji.get(trans['from_level'], '❓')
            to_emoji = alert_emoji.get(trans['to_level'], '❓')
            arrow = "⬆" if trans['direction'] == 'escalating' else "⬇"
            print(f"  {date_str}: {from_emoji} {trans['from_level']} → {to_emoji} {trans['to_level']} {arrow} (score: {trans['score']:.1f})")

    # Show sample data
    print("\nSAMPLE STRESS SCORES (Last 10 months):")
    print("="*60)

    valid_df = stress_df.dropna(subset=['composite_score'])
    sample = valid_df[['gdp_score', 'cpi_score', 'unemployment_score', 'composite_score', 'alert_level']].tail(10)

    # Format for display
    pd.set_option('display.float_format', '{:.1f}'.format)
    print(sample.to_string())

    # Show contributions
    print("\nCOMPONENT CONTRIBUTIONS (Last 5 months):")
    print("="*60)
    contributions = get_component_contributions(stress_df)
    sample_contrib = contributions.tail(5)
    print(sample_contrib.to_string())

    print("\n✓ Stress scorer test complete!")
