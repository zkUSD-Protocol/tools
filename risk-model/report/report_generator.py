import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from datetime import datetime
import json
from utils import get_protocol_status, get_health_status_labels, HEALTH_FACTOR_THRESHOLDS
import numpy as np
import scipy.stats as stats
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches


class ReportGenerator:
    def __init__(self, csv_path, distributions_path=None):
        """Initialize report generator with path to CSV files"""
        self.csv_path = Path(csv_path)
        self.df = pd.read_csv(self.csv_path)

        # Load distributions if available
        self.distributions_path = distributions_path
        if distributions_path:
            self.distributions_df = pd.read_csv(Path(distributions_path))
        else:
            # Try to infer distributions path from results path
            potential_dist_path = self.csv_path.parent / \
                f"health_distributions_{self.csv_path.name.split('_')[-1]}"
            if potential_dist_path.exists():
                self.distributions_df = pd.read_csv(potential_dist_path)
                self.distributions_path = potential_dist_path
            else:
                self.distributions_df = None

        self.output_dir = self._create_output_directory()
        self.scenarios = self.df['scenario_name'].unique()

        # Set style for all plots
        sns.set_theme()
        sns.set_palette("husl")

    def _create_output_directory(self):
        """Create directory for storing report outputs"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = Path(f'results/analysis_{timestamp}')
        output_dir.mkdir(parents=True, exist_ok=True)

        # Create subdirectory for each scenario
        for scenario in self.df['scenario_name'].unique():
            (output_dir / scenario).mkdir(exist_ok=True)

        return output_dir

    def generate_full_report(self):
        """Generate all report components"""
        print("Generating full analysis report...")

        # Generate executive summary first
        self.generate_executive_summary()
        # self.generate_risk_heatmap()
        self.generate_risk_heatmap_grids()
        # Generate individual scenario reports
        for scenario in self.scenarios:
            print(f"\nGenerating reports for scenario: {scenario}")
            scenario_df = self.df[self.df['scenario_name'] == scenario]

            # Generate detailed step-by-step breakdown for this scenario
            self.generate_step_by_step_breakdown(scenario, scenario_df)

            self.plot_protocol_health(scenario, scenario_df)
            self.plot_liquidation_metrics(scenario, scenario_df)
            self.plot_collateralization_ratio(scenario, scenario_df)
            self.plot_vault_distribution(scenario, scenario_df)
            self.plot_health_factor_distribution(scenario, scenario_df)

        # Generate overall summary statistics
        self.generate_summary_statistics()

        print(f"\nReport generated successfully in: {self.output_dir}")

    def generate_executive_summary(self):
        """Generate executive summary of all scenarios"""
        # Import health status labels from utils
        from utils import get_health_status_labels, HEALTH_FACTOR_THRESHOLDS

        # Get health status labels
        labels = get_health_status_labels()

        summary = []

        for scenario in self.scenarios:
            scenario_df = self.df[self.df['scenario_name'] == scenario]
            final_state = scenario_df.iloc[-1]
            initial_state = scenario_df.iloc[0]

            # Get scenario parameters
            scenario_params = {
                'num_vaults': int(final_state['num_vaults']),
                'price_drop_percentage': float((self.df['price'].iloc[0] - final_state['price']) /
                                               self.df['price'].iloc[0] * 100),
                'simulation_duration': float(final_state['simulation_hour']),
                'health_factor_mean': float(initial_state.get('health_factor_mean', 150)),
                'health_factor_std': float(initial_state.get('health_factor_std', 30)),
                'min_health_factor': float(initial_state.get('min_health_factor', 105)),
            }

            # Calculate final metrics
            final_metrics = {
                'protocol_health_factor': float(final_state['protocol_health_factor']),
                'total_collateral': float(final_state['total_collateral']),
                'total_debt': float(final_state['total_debt']),
                'num_liquidated_vaults': int(final_state['num_liquidated_vaults']),
                'collateralization_ratio': float(final_state['collateralization_ratio']),
                'num_healthy_vaults': int(final_state['num_healthy_vaults']),
                'num_at_risk_vaults': int(final_state['num_at_risk_vaults']),
                'num_liquidatable_vaults': int(final_state['num_liquidatable_vaults']),
                'num_insolvent_vaults': int(final_state.get('num_insolvent_vaults', 0)),
            }

            # Get protocol status
            protocol_status = get_protocol_status(
                final_metrics['protocol_health_factor'],
                scenario_params['num_vaults'] -
                final_metrics['num_liquidated_vaults']
            )

            summary.append({
                'scenario_name': scenario,
                'parameters': scenario_params,
                'final_metrics': final_metrics,
                'protocol_status': protocol_status
            })

        # Write executive summary to markdown file
        with open(self.output_dir / 'executive_summary.md', 'w') as f:
            f.write("# Risk Model Simulation Executive Summary\n\n")

            # Add health factor legend
            f.write("## Health Factor Categories\n\n")
            f.write(f"- **{labels['HEALTHY']}**\n")
            f.write(f"- **{labels['AT_RISK']}**\n")
            f.write(f"- **{labels['LIQUIDATABLE']}**\n")
            f.write(f"- **{labels['INSOLVENT']}**\n")
            f.write(f"- **{labels['LIQUIDATED']}**\n\n")
            f.write("---\n\n")

            for scenario_summary in summary:
                f.write(f"## {scenario_summary['scenario_name']}\n\n")

                f.write("### Scenario Parameters\n")
                f.write(
                    f"- Number of Vaults: {scenario_summary['parameters']['num_vaults']:,}\n")
                f.write(
                    f"- Price Drop: {scenario_summary['parameters']['price_drop_percentage']:.1f}%\n")
                f.write(
                    f"- Duration: {scenario_summary['parameters']['simulation_duration']:.1f} hours\n")
                f.write(
                    f"- Health Factor Distribution: Mean {scenario_summary['parameters']['health_factor_mean']:.0f}, "
                    f"Std {scenario_summary['parameters']['health_factor_std']:.0f}, "
                    f"Min {scenario_summary['parameters']['min_health_factor']:.0f}\n\n")

                f.write("### Final State\n")
                f.write(
                    f"- Protocol Status: **{scenario_summary['protocol_status']}**\n")
                f.write(
                    f"- Protocol Health Factor: {scenario_summary['final_metrics']['protocol_health_factor']:.1f}\n")
                f.write(
                    f"- Total Collateral: {scenario_summary['final_metrics']['total_collateral']:,.0f} MINA\n")
                f.write(
                    f"- Total Debt: ${scenario_summary['final_metrics']['total_debt']:,.2f}\n")
                f.write(
                    f"- Collateralization Ratio: {scenario_summary['final_metrics']['collateralization_ratio']:.1f}%\n\n")

                # Add vault distribution section
                total_vaults = scenario_summary['parameters']['num_vaults']
                f.write("### Vault Distribution\n")
                f.write(f"- {labels['HEALTHY']}: {scenario_summary['final_metrics']['num_healthy_vaults']:,} "
                        f"({scenario_summary['final_metrics']['num_healthy_vaults']/total_vaults*100:.1f}%)\n")
                f.write(f"- {labels['AT_RISK']}: {scenario_summary['final_metrics']['num_at_risk_vaults']:,} "
                        f"({scenario_summary['final_metrics']['num_at_risk_vaults']/total_vaults*100:.1f}%)\n")
                f.write(f"- {labels['LIQUIDATABLE']}: {scenario_summary['final_metrics']['num_liquidatable_vaults']:,} "
                        f"({scenario_summary['final_metrics']['num_liquidatable_vaults']/total_vaults*100:.1f}%)\n")
                f.write(f"- {labels['INSOLVENT']}: {scenario_summary['final_metrics']['num_insolvent_vaults']:,} "
                        f"({scenario_summary['final_metrics']['num_insolvent_vaults']/total_vaults*100:.1f}%)\n")
                f.write(f"- {labels['LIQUIDATED']}: {scenario_summary['final_metrics']['num_liquidated_vaults']:,} "
                        f"({scenario_summary['final_metrics']['num_liquidated_vaults']/total_vaults*100:.1f}%)\n\n")

                f.write("---\n\n")

        # Also save raw data for potential future use
        with open(self.output_dir / 'executive_summary.json', 'w') as f:
            json.dump(summary, f, indent=2)

    def generate_risk_heatmap_grids(self):
        """
        Generate multiple heatmaps, one per scale, showing protocol health factor
        by `risk_level` vs. `price_drop`.
        """
        # 1) Sort and keep only final row of each scenario_name+iteration
        df_sorted = self.df.sort_values(by='step', ascending=True)

        # Create two separate dataframes - one for end of price drop, one for final state
        # For price drop phase, get the last row of each scenario where simulation_phase is 'price_drop'
        df_price_drop_end = df_sorted[df_sorted['simulation_phase'] == 'price_drop'].drop_duplicates(
            subset=['scenario_name', 'iteration'],
            keep='last'
        )

        # For final state, get the last row of each scenario regardless of phase
        df_final = df_sorted.drop_duplicates(
            subset=['scenario_name', 'iteration'],
            keep='last'
        )

        # 2) Parse scenario_name => (price_drop, risk_level, scale)
        def parse_scenario_name(name: str):
            parts = name.split('_')

            # Handle new format with duration in days
            # Example: "30%_drop_1_day_low_risk_low_scale"
            if "day" in name:
                # e.g. "30%_drop_1_day"
                price_drop = f"{parts[0]}_drop_{parts[2]}_{parts[3]}"
                risk_level = parts[4] + "_" + parts[5]  # e.g. "low_risk"
                scale = parts[6] + "_" + parts[7]       # e.g. "low_scale"
            else:
                # Handle old format for backward compatibility
                price_drop = parts[0]           # e.g. "20%"
                risk_level = parts[2] + "_" + parts[3]  # e.g. "low_risk"
                scale = parts[4] + "_" + parts[5]       # e.g. "low_scale"

            return price_drop, risk_level, scale

        # Apply parsing to both dataframes
        df_price_drop_end[['price_drop', 'risk_level', 'scale']] = df_price_drop_end['scenario_name'].apply(
            lambda x: pd.Series(parse_scenario_name(x))
        )

        df_final[['price_drop', 'risk_level', 'scale']] = df_final['scenario_name'].apply(
            lambda x: pd.Series(parse_scenario_name(x))
        )

        # Import thresholds for color mapping
        from utils import HEALTH_FACTOR_THRESHOLDS
        import matplotlib.colors as mcolors
        import matplotlib.patches as mpatches

        # 4) Generate a separate heatmap for each scale and each phase
        unique_scales = df_final['scale'].unique()

        # Define the order of risk levels (high -> medium -> low)
        risk_level_order = ['high_risk', 'medium_risk', 'low_risk']

        # Define the order of price drops (from smallest to largest drop)
        # This ensures consistent ordering in the heatmap
        price_drop_order = [
            "30%_drop_1_day", "50%_drop_1_day",
            "40%_drop_3_days", "60%_drop_3_days",
            "45%_drop_5_days", "70%_drop_5_days",
            "50%_drop_7_days", "80%_drop_7_days"
        ]

        # Function to create heatmaps for a given dataframe and phase name
        def create_heatmaps_for_phase(df, phase_name):
            for sc in unique_scales:
                subset = df[df['scale'] == sc]

                if subset.empty:
                    print(f"No data for scale {sc} in {phase_name} phase")
                    continue

                # Filter to only include price drops that exist in the data
                available_price_drops = [
                    p for p in price_drop_order if p in subset['price_drop'].unique()]

                # Pivot using protocol_health_factor
                pivot_data = subset.pivot(
                    index='risk_level',
                    columns='price_drop',
                    values='protocol_health_factor'
                )

                # Reindex to ensure consistent ordering
                pivot_data = pivot_data.reindex(risk_level_order)
                pivot_data = pivot_data.reindex(columns=available_price_drops)

                pivot_data.index = pivot_data.index.map({
                    'high_risk': 'aggressive_risk',
                    'medium_risk': 'balanced_risk',
                    'low_risk': 'conservative_risk'
                })

                # Get the number of vaults for this scale
                num_of_vaults = subset['num_vaults'].unique()[0]

                # Create a completely new approach using matplotlib directly
                # Increased height for legend
                # Increased width for more columns
                fig, ax = plt.subplots(figsize=(14, 9))

                # Define color ranges based on health factor thresholds
                # Red for below insolvency, orange for below liquidation, yellow for at risk, green for healthy
                cmap = mcolors.LinearSegmentedColormap.from_list('health_factor_cmap', [
                    # 0 to insolvency
                    (0, 'darkred'),
                    # insolvency to liquidation
                    (HEALTH_FACTOR_THRESHOLDS['INSOLVENCY']/200, 'red'),
                    # liquidation to at risk
                    (HEALTH_FACTOR_THRESHOLDS['LIQUIDATION']/200, 'orange'),
                    # at risk to safe
                    (HEALTH_FACTOR_THRESHOLDS['SAFE']/200, 'yellowgreen'),
                    # safe and above
                    (1, 'green')
                ])

                # Create a normalized colormap
                norm = mcolors.Normalize(vmin=0, vmax=200)

                # Create the heatmap manually
                rows = pivot_data.index
                cols = pivot_data.columns

                # Create the grid
                for i, row in enumerate(rows):
                    for j, col in enumerate(cols):
                        value = pivot_data.loc[row, col]
                        if pd.notna(value):  # Only process non-NaN values
                            color = cmap(norm(value))
                            rect = plt.Rectangle(
                                (j, i), 1, 1, color=color, edgecolor='white', linewidth=2)
                            ax.add_patch(rect)
                            # Add text annotation
                            ax.text(j + 0.5, i + 0.5, f"{value:.1f}", ha='center', va='center',
                                    color='white' if value < 120 else 'black', fontsize=12, fontweight='bold')

                # Set the limits and labels
                ax.set_xlim(0, len(cols))
                ax.set_ylim(0, len(rows))
                ax.set_xticks([i + 0.5 for i in range(len(cols))])
                ax.set_yticks([i + 0.5 for i in range(len(rows))])
                # Rotate labels for better readability
                ax.set_xticklabels(cols, rotation=45, ha='right')
                ax.set_yticklabels(rows)

                # Add title and labels
                plt.title(
                    f"Protocol Health Factor Heatmap - {num_of_vaults} Vaults - {phase_name}", fontsize=14)
                plt.xlabel("Price Drop", fontsize=12)
                plt.ylabel("Overall Protocol Risk Level", fontsize=12)

                # Create a separate colorbar
                # [left, bottom, width, height]
                cbar_ax = fig.add_axes([0.92, 0.25, 0.02, 0.6])
                sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
                sm.set_array([])
                cbar = fig.colorbar(sm, cax=cbar_ax)
                cbar.set_label('Protocol Health Factor', fontsize=12)

                # Add threshold lines to colorbar (without text labels)
                thresholds = [
                    (HEALTH_FACTOR_THRESHOLDS['INSOLVENCY'], 'darkred'),
                    (HEALTH_FACTOR_THRESHOLDS['LIQUIDATION'], 'red'),
                    (HEALTH_FACTOR_THRESHOLDS['SAFE'], 'green')
                ]

                # Create a separate legend/key for the thresholds
                legend_elements = [
                    mpatches.Patch(
                        color='green', label=f'Healthy (HF ≥ {HEALTH_FACTOR_THRESHOLDS["SAFE"]})'),
                    mpatches.Patch(
                        color='yellowgreen', label=f'At Risk ({HEALTH_FACTOR_THRESHOLDS["LIQUIDATION"]} ≤ HF < {HEALTH_FACTOR_THRESHOLDS["SAFE"]})'),
                    mpatches.Patch(
                        color='orange', label=f'Severe Risk ({HEALTH_FACTOR_THRESHOLDS["INSOLVENCY"]} ≤ HF < {HEALTH_FACTOR_THRESHOLDS["LIQUIDATION"]})'),
                    mpatches.Patch(
                        color='darkred', label=f'Insolvent (HF < {HEALTH_FACTOR_THRESHOLDS["INSOLVENCY"]})')
                ]

                # Add the legend at the bottom of the plot
                legend = ax.legend(handles=legend_elements, loc='upper center',
                                   bbox_to_anchor=(0.5, -0.3), ncol=2, fontsize=10,
                                   title="Health Factor Categories", title_fontsize=12)

                # Adjust layout
                # Make room for legend at bottom
                plt.subplots_adjust(right=0.9, bottom=0.3)

                # Save the figure
                plt.savefig(
                    self.output_dir / f"health_factor_heatmap_{sc}_{phase_name}.png", dpi=300, bbox_inches='tight')
                plt.close()

                # Also create a second heatmap showing the percentage of liquidated vaults
                # Using the same manual approach for consistency
                pivot_liquidated = subset.pivot(
                    index='risk_level',
                    columns='price_drop',
                    values='num_liquidated_vaults'
                )

                # Reindex to ensure consistent ordering
                pivot_liquidated = pivot_liquidated.reindex(risk_level_order)
                pivot_liquidated = pivot_liquidated.reindex(
                    columns=available_price_drops)

                pivot_liquidated.index = pivot_liquidated.index.map({
                    'high_risk': 'aggressive_risk',
                    'medium_risk': 'balanced_risk',
                    'low_risk': 'conservative_risk'
                })

                # Calculate percentage of liquidated vaults
                for col in pivot_liquidated.columns:
                    pivot_liquidated[col] = (
                        pivot_liquidated[col] / num_of_vaults) * 100

                # Create liquidation heatmap
                # Increased height for legend
                # Increased width for more columns
                fig, ax = plt.subplots(figsize=(14, 9))

                # Define color ranges for liquidation percentage
                liquidation_cmap = mcolors.LinearSegmentedColormap.from_list('liquidation_cmap', [
                    (0, 'lightyellow'),    # 0% liquidated
                    (0.25, 'yellow'),      # 25% liquidated
                    (0.5, 'orange'),       # 50% liquidated
                    (0.75, 'orangered'),   # 75% liquidated
                    (1, 'darkred')         # 100% liquidated
                ])

                # Create a normalized colormap for liquidation
                liquidation_norm = mcolors.Normalize(vmin=0, vmax=100)

                # Create the heatmap manually
                for i, row in enumerate(rows):
                    for j, col in enumerate(cols):
                        value = pivot_liquidated.loc[row, col]
                        if pd.notna(value):  # Only process non-NaN values
                            color = liquidation_cmap(liquidation_norm(value))
                            rect = plt.Rectangle(
                                (j, i), 1, 1, color=color, edgecolor='white', linewidth=2)
                            ax.add_patch(rect)
                            # Add text annotation
                            ax.text(j + 0.5, i + 0.5, f"{value:.1f}%", ha='center', va='center',
                                    color='black' if value < 50 else 'white', fontsize=12, fontweight='bold')

                # Set the limits and labels
                ax.set_xlim(0, len(cols))
                ax.set_ylim(0, len(rows))
                ax.set_xticks([i + 0.5 for i in range(len(cols))])
                ax.set_yticks([i + 0.5 for i in range(len(rows))])
                # Rotate labels for better readability
                ax.set_xticklabels(cols, rotation=45, ha='right')
                ax.set_yticklabels(rows)

                # Add title and labels
                plt.title(
                    f"Liquidated Vaults Percentage - {num_of_vaults} Vaults - {phase_name}", fontsize=14)
                plt.xlabel("Price Drop", fontsize=12)
                plt.ylabel("Overall Protocol Risk Level", fontsize=12)

                # Create a separate colorbar
                # [left, bottom, width, height]
                cbar_ax = fig.add_axes([0.92, 0.3, 0.02, 0.4])
                sm_liq = plt.cm.ScalarMappable(
                    cmap=liquidation_cmap, norm=liquidation_norm)
                sm_liq.set_array([])
                cbar_liq = fig.colorbar(sm_liq, cax=cbar_ax)
                cbar_liq.set_label('Liquidated Vaults (%)', fontsize=12)

                # Add threshold lines to colorbar (without text labels)
                liquidation_thresholds = [
                    (25, 'yellow'),
                    (50, 'orange'),
                    (75, 'orangered')
                ]

                for threshold, color in liquidation_thresholds:
                    # Calculate the normalized position (0-1) within the colorbar
                    y_pos = threshold / 100

                    # Add a horizontal line at the threshold position
                    cbar_liq.ax.plot([0, 1], [y_pos, y_pos], color=color,
                                     linewidth=2, transform=cbar_liq.ax.transAxes)

                # Create a separate legend/key for the liquidation thresholds
                liquidation_legend_elements = [
                    mpatches.Patch(color='lightyellow',
                                   label='Low Impact (0-25%)'),
                    mpatches.Patch(
                        color='yellow', label='Moderate Impact (25-50%)'),
                    mpatches.Patch(
                        color='orange', label='High Impact (50-75%)'),
                    mpatches.Patch(color='darkred',
                                   label='Severe Impact (75-100%)')
                ]

                # Add the legend at the bottom of the plot
                legend = ax.legend(handles=liquidation_legend_elements, loc='upper center',
                                   bbox_to_anchor=(0.5, -0.3), ncol=2, fontsize=10,
                                   title="Liquidation Impact Categories", title_fontsize=12)

                # Adjust layout
                # Make room for legend at bottom
                plt.subplots_adjust(right=0.9, bottom=0.3)

                # Save the figure
                plt.savefig(
                    self.output_dir / f"liquidated_vaults_heatmap_{sc}_{phase_name}.png", dpi=300, bbox_inches='tight')
                plt.close()

        # Create heatmaps for both phases
        create_heatmaps_for_phase(df_price_drop_end, "price_drop_end")
        create_heatmaps_for_phase(df_final, "final_state")

    def plot_protocol_health(self, scenario, scenario_df):
        """Plot protocol health factor evolution for a single scenario"""
        plt.figure(figsize=(12, 6))

        # Add color coding for different phases
        colors = {
            'initial': 'green',
            'price_drop': 'red',
            'recovery': 'blue'
        }

        # Plot each phase with different colors
        for phase in ['initial', 'price_drop', 'recovery']:
            phase_df = scenario_df[scenario_df['simulation_phase'] == phase]
            if not phase_df.empty:
                sns.lineplot(
                    data=phase_df,
                    x='simulation_hour',
                    y='protocol_health_factor',
                    errorbar=None,
                    label=f"{phase.replace('_', ' ').title()} Phase",
                    color=colors.get(phase)
                )

        # Add vertical line at the end of price drop phase
        price_drop_end = scenario_df[scenario_df['simulation_phase']
                                     == 'price_drop']['simulation_hour'].max()
        if not pd.isna(price_drop_end):
            plt.axvline(x=price_drop_end, color='black', linestyle='--',
                        label='End of Price Drop')

        plt.title(f'Protocol Health Factor Evolution - {scenario}')
        plt.xlabel('Simulation Hours')
        plt.ylabel('Health Factor')
        plt.grid(True)
        plt.legend()
        plt.tight_layout()

        plt.savefig(self.output_dir / scenario / 'protocol_health.png')
        plt.close()

    def plot_liquidation_metrics(self, scenario, scenario_df):
        """Plot liquidation-related metrics for a single scenario"""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

        # Add color coding for different phases
        colors = {
            'initial': 'green',
            'price_drop': 'red',
            'recovery': 'blue'
        }

        # Plot each phase with different colors for liquidated vaults
        for phase in ['initial', 'price_drop', 'recovery']:
            phase_df = scenario_df[scenario_df['simulation_phase'] == phase]
            if not phase_df.empty:
                sns.lineplot(
                    data=phase_df,
                    x='simulation_hour',
                    y='num_liquidated_vaults',
                    errorbar=None,
                    ax=ax1,
                    label=f"{phase.replace('_', ' ').title()} Phase",
                    color=colors.get(phase)
                )

        ax1.set_title(f'Number of Liquidated Vaults Over Time - {scenario}')
        ax1.set_xlabel('Simulation Hours')
        ax1.set_ylabel('Number of Liquidated Vaults')
        ax1.grid(True)
        ax1.legend()

        # Plot each phase with different colors for liquidation queue
        for phase in ['initial', 'price_drop', 'recovery']:
            phase_df = scenario_df[scenario_df['simulation_phase'] == phase]
            if not phase_df.empty:
                sns.lineplot(
                    data=phase_df,
                    x='simulation_hour',
                    y='liquidation_queue_size',
                    errorbar=None,
                    ax=ax2,
                    label=f"{phase.replace('_', ' ').title()} Phase",
                    color=colors.get(phase)
                )

        # Add vertical line at the end of price drop phase
        price_drop_end = scenario_df[scenario_df['simulation_phase']
                                     == 'price_drop']['simulation_hour'].max()
        if not pd.isna(price_drop_end):
            ax1.axvline(x=price_drop_end, color='black', linestyle='--',
                        label='End of Price Drop')
            ax2.axvline(x=price_drop_end, color='black', linestyle='--',
                        label='End of Price Drop')

        ax2.set_title(f'Liquidation Queue Size Over Time - {scenario}')
        ax2.set_xlabel('Simulation Hours')
        ax2.set_ylabel('Queue Size')
        ax2.grid(True)
        ax2.legend()

        plt.tight_layout()
        plt.savefig(self.output_dir / scenario / 'liquidation_metrics.png')
        plt.close()

    def plot_collateralization_ratio(self, scenario, scenario_df):
        """Plot protocol collateralization ratio trends for a single scenario"""
        plt.figure(figsize=(12, 6))

        # Add color coding for different phases
        colors = {
            'initial': 'green',
            'price_drop': 'red',
            'recovery': 'blue'
        }

        # Plot each phase with different colors
        for phase in ['initial', 'price_drop', 'recovery']:
            phase_df = scenario_df[scenario_df['simulation_phase'] == phase]
            if not phase_df.empty:
                sns.lineplot(
                    data=phase_df,
                    x='simulation_hour',
                    y='collateralization_ratio',
                    errorbar=None,
                    label=f"{phase.replace('_', ' ').title()} Phase",
                    color=colors.get(phase)
                )

        # Add vertical line at the end of price drop phase
        price_drop_end = scenario_df[scenario_df['simulation_phase']
                                     == 'price_drop']['simulation_hour'].max()
        if not pd.isna(price_drop_end):
            plt.axvline(x=price_drop_end, color='black', linestyle='--',
                        label='End of Price Drop')

        plt.title(f'Collateralization Ratio Over Time - {scenario}')
        plt.xlabel('Simulation Hours')
        plt.ylabel('Protocol Collateralization Ratio (%)')
        plt.grid(True)
        plt.legend()
        plt.tight_layout()

        plt.savefig(self.output_dir / scenario /
                    'protocol_collateralization_ratio.png')
        plt.close()

    def plot_vault_distribution(self, scenario, scenario_df):
        """Plot vault health distribution over time for a single scenario"""
        plt.figure(figsize=(12, 6))

        # Import health status labels from utils
        from utils import get_health_status_labels

        # Get health status labels
        labels = get_health_status_labels()

        # Create stacked area plot
        plt.stackplot(scenario_df['simulation_hour'],
                      [scenario_df['num_healthy_vaults'],
                      scenario_df['num_at_risk_vaults'],
                      scenario_df['num_liquidatable_vaults'],
                      scenario_df['num_insolvent_vaults'],
                      scenario_df['num_liquidated_vaults']],
                      labels=[labels['HEALTHY'],
                              labels['AT_RISK'],
                              labels['LIQUIDATABLE'],
                              labels['INSOLVENT'],
                              labels['LIQUIDATED']],
                      alpha=0.7,
                      colors=['green', 'yellow', 'orange', 'red', 'black'])

        # Add vertical line at the end of price drop phase
        price_drop_end = scenario_df[scenario_df['simulation_phase']
                                     == 'price_drop']['simulation_hour'].max()
        if not pd.isna(price_drop_end):
            plt.axvline(x=price_drop_end, color='black', linestyle='--',
                        label='End of Price Drop')

        plt.title(f'Vault Distribution Over Time - {scenario}')
        plt.xlabel('Simulation Hours')
        plt.ylabel('Number of Vaults')
        plt.legend(loc='center left', bbox_to_anchor=(1, 0.5))
        plt.grid(True)
        plt.tight_layout()

        plt.savefig(self.output_dir / scenario / 'vault_distribution.png')
        plt.close()

    def plot_health_factor_distribution(self, scenario, scenario_df):
        """Plot the initial health factor distribution for a scenario"""
        # First check if we have a distributions DataFrame
        if self.distributions_df is not None:
            # Get the distribution data for this scenario
            scenario_dist = self.distributions_df[self.distributions_df['scenario_name'] == scenario]

            if not scenario_dist.empty:
                # Use the first row (should be only one per scenario if using iteration=0)
                dist_data = scenario_dist.iloc[0]

                try:
                    # Parse the string values back to lists
                    hist_values = [float(x) for x in str(
                        dist_data['hf_hist_values']).split(',')]
                    bin_edges = [float(x) for x in str(
                        dist_data['hf_hist_bins']).split(',')]
                    mean_hf = float(dist_data['hf_mean'])
                    median_hf = float(dist_data['hf_median'])
                    std_hf = float(dist_data['hf_std'])

                    # Create plot using the histogram data
                    plt.figure(figsize=(12, 6))
                    plt.bar(bin_edges[:-1], hist_values, width=np.diff(bin_edges),
                            align='edge', alpha=0.7, edgecolor='black')

                    # Add KDE curve (optional)
                    x = np.linspace(100, 300, 1000)
                    if sum(hist_values) > 0:  # Ensure we have data
                        kde = stats.gaussian_kde(
                            np.repeat(bin_edges[:-1], np.round(hist_values).astype(int)))
                        plt.plot(x, kde(x) * sum(hist_values) * (bin_edges[1] - bin_edges[0]),
                                 'r-', linewidth=2)

                    use_synthetic = False
                except (ValueError, TypeError) as e:
                    print(
                        f"Error parsing distribution data for {scenario}: {e}")
                    use_synthetic = True
            else:
                use_synthetic = True
        else:
            # Fall back to checking the main DataFrame
            # Get the first row data (initial state)
            initial_data = scenario_df.iloc[0]

            # Check if we have histogram data
            if 'hf_hist_values' in initial_data and 'hf_hist_bins' in initial_data:
                try:
                    # Parse the string values back to lists
                    hist_values = [float(x) for x in str(
                        initial_data['hf_hist_values']).split(',')]
                    bin_edges = [float(x) for x in str(
                        initial_data['hf_hist_bins']).split(',')]
                    mean_hf = float(initial_data['hf_mean'])
                    median_hf = float(initial_data['hf_median'])
                    std_hf = float(initial_data['hf_std'])

                    # Create plot using the histogram data
                    plt.figure(figsize=(12, 6))
                    plt.bar(bin_edges[:-1], hist_values, width=np.diff(bin_edges),
                            align='edge', alpha=0.7, edgecolor='black')

                    # Add KDE curve (optional)
                    x = np.linspace(100, 300, 1000)
                    if sum(hist_values) > 0:  # Ensure we have data
                        kde = stats.gaussian_kde(
                            np.repeat(bin_edges[:-1], np.round(hist_values).astype(int)))
                        plt.plot(x, kde(x) * sum(hist_values) * (bin_edges[1] - bin_edges[0]),
                                 'r-', linewidth=2)
                except (ValueError, TypeError) as e:
                    # If there's any error parsing the data, fall back to synthetic
                    print(f"Error parsing histogram data for {scenario}: {e}")
                    use_synthetic = True
                else:
                    use_synthetic = False
            else:
                use_synthetic = True

        if use_synthetic:
            # Fall back to synthetic generation
            mean_hf = initial_data.get('health_factor_mean', 150)
            std_hf = initial_data.get('health_factor_std', 30)
            min_hf = initial_data.get('min_health_factor', 105)
            num_vaults = initial_data.get('num_vaults', 1000)

            # Generate synthetic health factors using log-normal distribution
            phi = std_hf / mean_hf  # Coefficient of variation
            sigma = np.sqrt(np.log(1 + phi**2))
            mu = np.log(mean_hf) - 0.5 * sigma**2

            # Generate synthetic health factors
            synthetic_hfs = np.array([
                max(min_hf, stats.lognorm.rvs(s=sigma, scale=np.exp(mu)))
                for _ in range(num_vaults)
            ])

            # Calculate statistics
            mean_hf = np.mean(synthetic_hfs)
            median_hf = np.median(synthetic_hfs)
            std_hf = np.std(synthetic_hfs)

            # Create plot
            plt.figure(figsize=(12, 6))
            sns.histplot(synthetic_hfs, bins=30, kde=True)
            print(f"Warning: Using synthetic health factors for {scenario}")

        # Add vertical lines for key thresholds and statistics
        plt.axvline(x=HEALTH_FACTOR_THRESHOLDS['INSOLVENCY'], color='darkred', linestyle='--',
                    label=f"Insolvency Threshold (HF < {HEALTH_FACTOR_THRESHOLDS['INSOLVENCY']})")
        plt.axvline(x=HEALTH_FACTOR_THRESHOLDS['LIQUIDATION'], color='red', linestyle='--',
                    label=f"Liquidation Threshold (HF < {HEALTH_FACTOR_THRESHOLDS['LIQUIDATION']})")
        plt.axvline(x=HEALTH_FACTOR_THRESHOLDS['SAFE'], color='green', linestyle='--',
                    label=f"Safe Threshold (HF ≥ {HEALTH_FACTOR_THRESHOLDS['SAFE']})")
        plt.axvline(x=mean_hf, color='blue', linestyle='-',
                    label=f'Mean: {mean_hf:.1f}')
        plt.axvline(x=median_hf, color='purple', linestyle='-',
                    label=f'Median: {median_hf:.1f}')

        # Add colored background regions
        plt.axvspan(0, HEALTH_FACTOR_THRESHOLDS['INSOLVENCY'],
                    alpha=0.1, color='darkred', label='_Insolvent')
        plt.axvspan(HEALTH_FACTOR_THRESHOLDS['INSOLVENCY'], HEALTH_FACTOR_THRESHOLDS['LIQUIDATION'],
                    alpha=0.1, color='red', label='_Liquidatable')
        plt.axvspan(HEALTH_FACTOR_THRESHOLDS['LIQUIDATION'], HEALTH_FACTOR_THRESHOLDS['SAFE'],
                    alpha=0.1, color='yellow', label='_At Risk')
        plt.axvspan(
            HEALTH_FACTOR_THRESHOLDS['SAFE'], 300, alpha=0.1, color='green', label='_Healthy')

        # Add labels and title
        plt.xlabel('Initial Health Factor')
        plt.ylabel('Number of Vaults')
        plt.title(
            f'Distribution of Initial Health Factors - {scenario}\nMean: {mean_hf:.1f}, Median: {median_hf:.1f}, Std: {std_hf:.1f}')
        plt.legend()
        plt.grid(True)
        plt.tight_layout()

        # Save the plot
        plt.savefig(self.output_dir / scenario /
                    'health_factor_distribution.png')
        plt.close()

    def generate_summary_statistics(self):
        """Generate summary statistics for each scenario"""
        summary_stats = self.df.groupby('scenario_name').agg({
            'protocol_health_factor': ['mean', 'min', 'max'],
            'collateralization_ratio': ['mean', 'min', 'max'],
            'num_liquidated_vaults': ['max'],
            'liquidation_queue_size': ['max']
        }).round(2)

        # Save to CSV
        summary_stats.to_csv(self.output_dir / 'summary_statistics.csv')

        # Also save individual scenario statistics
        for scenario in self.scenarios:
            scenario_stats = self.df[self.df['scenario_name'] == scenario].agg({
                'protocol_health_factor': ['mean', 'min', 'max'],
                'collateralization_ratio': ['mean', 'min', 'max'],
                'num_liquidated_vaults': ['max'],
                'liquidation_queue_size': ['max']
            }).round(2)

            scenario_stats.to_csv(
                self.output_dir / scenario / 'statistics.csv')

    def generate_step_by_step_breakdown(self, scenario, scenario_df):
        """Generate a detailed step-by-step breakdown of the simulation for a scenario"""
        # Create a text file for this scenario
        output_file = self.output_dir / scenario / 'step_by_step_breakdown.txt'

        with open(output_file, 'w') as f:
            # Write scenario information
            f.write(f"{'='*100}\n")
            f.write(f"SCENARIO: {scenario}\n")
            f.write(
                f"DESCRIPTION: {scenario_df['scenario_description'].iloc[0]}\n")
            f.write(f"{'='*100}\n\n")

            # Get initial parameters
            initial_row = scenario_df[scenario_df['step'] == 0].iloc[0]
            f.write(f"SIMULATION PARAMETERS:\n")
            f.write(f"{'-'*100}\n")
            f.write(f"Number of Vaults: {initial_row['num_vaults']}\n")
            f.write(
                f"Price Drop Duration: {initial_row['price_drop_duration']} hours\n")
            f.write(
                f"Collateralisation Ratio: {initial_row['collateralisation_ratio']}\n")
            f.write(
                f"Health Factor Mean: {initial_row['health_factor_mean']}\n")
            f.write(f"Health Factor Std: {initial_row['health_factor_std']}\n")
            f.write(f"Min Health Factor: {initial_row['min_health_factor']}\n")
            f.write(f"{'-'*100}\n\n")

            # Group by step to ensure we process each step only once
            steps = scenario_df.sort_values('step').groupby('step')

            # Process each step
            for step, step_data in steps:
                # Use the first row for each step (in case there are multiple iterations)
                row = step_data.iloc[0]

                # Determine the phase label
                phase = row['simulation_phase']
                phase_label = phase.replace('_', ' ').title()

                # For initial state
                if step == 0:
                    f.write("\nINITIAL STATE:\n")
                    self._write_protocol_status(f, row)
                    continue

                # For other steps, only print every 5th step (like in the simulation)
                if step % 5 == 0 or step == scenario_df['step'].max():
                    # For the final step, add a special header
                    if step == scenario_df['step'].max():
                        f.write(f"\nFINAL STATE (Step {step}):\n")
                    else:
                        # For regular steps, show the phase and simulation hour
                        simulation_hour = row['simulation_hour']

                        if phase == 'recovery':
                            # For recovery phase, show hours since price drop ended
                            price_drop_end_hour = scenario_df[scenario_df['simulation_phase']
                                                              == 'price_drop']['simulation_hour'].max()
                            recovery_hours = simulation_hour - price_drop_end_hour
                            f.write(
                                f"\nStep {step} ({phase_label} Phase, {recovery_hours:.1f} hours after drop):\n")
                        else:
                            f.write(f"\nStep {step} ({phase_label} Phase):\n")

                    self._write_protocol_status(f, row)

            # Add summary information at the end
            final_row = scenario_df.iloc[-1]
            total_steps = final_row['step']
            price_drop_duration = initial_row['price_drop_duration']

            # Calculate recovery duration
            simulation_duration = final_row['simulation_hour']
            price_drop_end_hour = scenario_df[scenario_df['simulation_phase']
                                              == 'price_drop']['simulation_hour'].max()
            recovery_duration = simulation_duration - price_drop_end_hour

            f.write(f"\n{'='*100}\n")
            f.write(f"SIMULATION SUMMARY:\n")
            f.write(f"Simulation completed after {total_steps} steps\n")
            f.write(f"Price drop duration: {price_drop_duration} hours\n")
            f.write(f"Recovery duration: {recovery_duration:.1f} hours\n")
            f.write(
                f"Total simulation time: {final_row['simulation_hour']:.1f} hours\n")
            f.write(f"{'='*100}\n")

        print(f"  - Created step-by-step breakdown for {scenario}")

    def _write_protocol_status(self, file, metrics):
        """Write detailed protocol status to the file"""
        file.write(f"{'-'*100}\n")
        file.write(f"PROTOCOL STATUS REPORT\n")
        file.write(f"{'-'*100}\n")
        file.write(
            f"Total Collateral: {metrics['total_collateral']:,.0f} MINA\n")
        file.write(f"Current Price: ${metrics['price']:.3f}\n")
        file.write(
            f"Protocol Health Factor: {metrics['protocol_health_factor']:.0f}\n")

        # Calculate number of active vaults
        active_vaults = metrics['num_healthy_vaults'] + \
            metrics['num_at_risk_vaults']
        file.write(
            f"Status: {get_protocol_status(metrics['protocol_health_factor'], active_vaults)}\n")

        file.write(
            f"Total Collateral Value: ${metrics['total_collateral_value']:,.2f}\n")
        file.write(f"Total Debt: ${metrics['total_debt']:,.2f}\n")

        # Calculate collateralization ratio
        if metrics['total_debt'] > 0:
            collat_ratio = metrics['total_collateral_value'] / \
                metrics['total_debt'] * 100
        else:
            collat_ratio = float('inf')
        file.write(f"Collateralization Ratio: {collat_ratio:.2f}%\n")

        file.write(
            f"Total Insolvent Collateral: {metrics['total_insolvent_collateral']:,.0f} MINA\n")
        file.write(
            f"Total Insolvent Collateral Value: ${metrics['total_insolvent_collateral_value']:,.2f}\n")
        file.write(
            f"Total Debt in Insolvent Vaults: ${metrics['total_debt_in_insolvent_vaults']:,.2f}\n")

        file.write(
            f"Initial Reserve Fund: ${metrics['initial_reserve_fund']:,.2f}\n")
        file.write(
            f"Reserve Fund: ${metrics['reserve_fund']:,.2f} ({metrics['reserve_fund_percentage']:.2f}%)\n")
        file.write(
            f"Reserve Fund Used: ${metrics['reserve_fund_used']:,.2f}\n")

        file.write("\nVault Distribution:\n")
        total_vaults = metrics['num_vaults']
        file.write(f"  Healthy Vaults: {metrics['num_healthy_vaults']} "
                   f"({metrics['num_healthy_vaults']/total_vaults*100:.1f}%)\n")
        file.write(f"  At Risk Vaults: {metrics['num_at_risk_vaults']} "
                   f"({metrics['num_at_risk_vaults']/total_vaults*100:.1f}%)\n")
        file.write(f"  Liquidatable Vaults: {metrics['num_liquidatable_vaults']} "
                   f"({metrics['num_liquidatable_vaults']/total_vaults*100:.1f}%)\n")
        file.write(f"  Insolvent Vaults: {metrics['num_insolvent_vaults']} "
                   f"({metrics['num_insolvent_vaults']/total_vaults*100:.1f}%)\n")
        file.write(f"  Liquidated Vaults: {metrics['num_liquidated_vaults']} "
                   f"({metrics['num_liquidated_vaults']/total_vaults*100:.1f}%)\n")

        # Add information about liquidation queue if available
        if 'liquidation_queue_size' in metrics:
            file.write(
                f"Liquidation Queue Size: {metrics['liquidation_queue_size']}\n")

        file.write(f"{'-'*100}\n")
