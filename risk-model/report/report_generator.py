import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from datetime import datetime
import json
from utils import get_protocol_status


class ReportGenerator:
    def __init__(self, csv_path):
        """Initialize report generator with path to CSV file"""
        self.df = pd.read_csv(csv_path)
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

            self.plot_protocol_health(scenario, scenario_df)
            self.plot_liquidation_metrics(scenario, scenario_df)
            self.plot_collateralization_ratio(scenario, scenario_df)
            self.plot_vault_distribution(scenario, scenario_df)

        # Generate overall summary statistics
        self.generate_summary_statistics()

        print(f"\nReport generated successfully in: {self.output_dir}")

    def generate_executive_summary(self):
        """Generate executive summary of all scenarios"""
        summary = []

        for scenario in self.scenarios:
            scenario_df = self.df[self.df['scenario_name'] == scenario]
            final_state = scenario_df.iloc[-1]

            # Get scenario parameters
            scenario_params = {
                'num_vaults': int(final_state['num_vaults']),
                'price_drop_percentage': float((self.df['price'].iloc[0] - final_state['price']) /
                                               self.df['price'].iloc[0] * 100),
                'simulation_duration': float(final_state['simulation_hour']),
                'min_health_factor': float(scenario_df['min_health_factor'].iloc[0]),
                'max_health_factor': float(scenario_df['max_health_factor'].iloc[0]),
            }

            # Calculate final metrics
            final_metrics = {
                'protocol_health_factor': float(final_state['protocol_health_factor']),
                'total_collateral': float(final_state['total_collateral']),
                'total_debt': float(final_state['total_debt']),
                'num_liquidated_vaults': int(final_state['num_liquidated_vaults']),
                'collateralization_ratio': float(final_state['collateralization_ratio']),
                # Add vault distribution metrics
                'num_healthy_vaults': int(final_state['num_healthy_vaults']),
                'num_at_risk_vaults': int(final_state['num_at_risk_vaults']),
                'num_liquidatable_vaults': int(final_state['num_liquidatable_vaults'])
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

            for scenario_summary in summary:
                f.write(f"## {scenario_summary['scenario_name']}\n\n")

                f.write("### Scenario Parameters\n")
                f.write(
                    f"- Number of Vaults: {scenario_summary['parameters']['num_vaults']:,}\n")
                f.write(
                    f"- Price Drop: {scenario_summary['parameters']['price_drop_percentage']:.1f}%\n")
                f.write(
                    f"- Duration: {scenario_summary['parameters']['simulation_duration']:.1f} hours\n")
                f.write(f"- Initial Health Factor Range: {scenario_summary['parameters']['min_health_factor']:.0f}-{
                        scenario_summary['parameters']['max_health_factor']:.0f}\n\n")

                f.write("### Final State\n")
                f.write(
                    f"- Protocol Status: **{scenario_summary['protocol_status']}**\n")
                f.write(f"- Protocol Health Factor: {
                        scenario_summary['final_metrics']['protocol_health_factor']:.1f}\n")
                f.write(
                    f"- Total Collateral: {scenario_summary['final_metrics']['total_collateral']:,.0f} MINA\n")
                f.write(
                    f"- Total Debt: ${scenario_summary['final_metrics']['total_debt']:,.2f}\n")
                f.write(f"- Collateralization Ratio: {
                        scenario_summary['final_metrics']['collateralization_ratio']:.1f}%\n\n")

                # Add vault distribution section
                total_vaults = scenario_summary['parameters']['num_vaults']
                f.write("### Vault Distribution\n")
                f.write(f"- Healthy Vaults: {scenario_summary['final_metrics']['num_healthy_vaults']:,} "
                        f"({scenario_summary['final_metrics']['num_healthy_vaults']/total_vaults*100:.1f}%)\n")
                f.write(f"- At Risk Vaults: {scenario_summary['final_metrics']['num_at_risk_vaults']:,} "
                        f"({scenario_summary['final_metrics']['num_at_risk_vaults']/total_vaults*100:.1f}%)\n")
                f.write(f"- Liquidatable Vaults: {scenario_summary['final_metrics']['num_liquidatable_vaults']:,} "
                        f"({scenario_summary['final_metrics']['num_liquidatable_vaults']/total_vaults*100:.1f}%)\n")
                f.write(f"- Liquidated Vaults: {scenario_summary['final_metrics']['num_liquidated_vaults']:,} "
                        f"({scenario_summary['final_metrics']['num_liquidated_vaults']/total_vaults*100:.1f}%)\n\n")

                f.write("---\n\n")

        # Also save raw data for potential future use
        with open(self.output_dir / 'executive_summary.json', 'w') as f:
            json.dump(summary, f, indent=2)

    def generate_risk_heatmap_grids(self):
        """
        Generate multiple heatmaps, one per scale, pivoting the final scenario data
        by `risk_level` vs. `price_drop`.
        """
        # 1) Sort and keep only final row of each scenario_name+iteration
        df_sorted = self.df.sort_values(by='step', ascending=True)
        df_final = df_sorted.drop_duplicates(
            subset=['scenario_name', 'iteration'],
            keep='last'
        )

        # 2) Parse scenario_name => (price_drop, risk_level, scale)
        def parse_scenario_name(name: str):
            parts = name.split('_')
            price_drop = parts[0]           # e.g. "20%"
            risk_level = parts[2] + "_" + parts[3]  # e.g. "low_risk"
            scale = parts[4] + "_" + parts[5]       # e.g. "low_scale"
            return price_drop, risk_level, scale

        df_final[['price_drop', 'risk_level', 'scale']] = df_final['scenario_name'].apply(
            lambda x: pd.Series(parse_scenario_name(x))
        )

        # 3) Calculate a numeric 'score' from final protocol status
        risk_scores = {
            "SUCCESSFULLY LIQUIDATED POSITIONS": 0,
            "VERY HEALTHY": 1,
            "HEALTHY": 2,
            "CAUTION": 3,
            "HIGH RISK": 4,
            "IMMINENT INSOLVENCY": 5,
            "INSOLVENT": 6,
        }

        def get_risk_score(row):
            status = get_protocol_status(
                row['protocol_health_factor'],
                row['num_vaults'] - row['num_liquidated_vaults']
            )
            return risk_scores[status]

        df_final['score'] = df_final.apply(get_risk_score, axis=1)

        # 4) Generate a separate heatmap for each scale
        unique_scales = df_final['scale'].unique()
        for sc in unique_scales:
            subset = df_final[df_final['scale'] == sc]

            # Define the order of risk levels (high -> medium -> low)
            risk_level_order = ['high_risk', 'medium_risk', 'low_risk']

            # Pivot
            pivot_data = subset.pivot(
                index='risk_level',
                columns='price_drop',
                values='score'
            )

            pivot_data = pivot_data.reindex(risk_level_order)

            pivot_data.index = pivot_data.index.map({
                'high_risk': 'aggressive_risk',
                'medium_risk': 'balanced_risk',
                'low_risk': 'conservative_risk'
            })

            # Plot
            plt.figure(figsize=(10, 8))
            ax = sns.heatmap(
                pivot_data,
                cmap='RdYlGn_r',
                annot=True,
                fmt='.0f',
                cbar_kws={'label': 'Risk Score'},
                linewidths=0.5,
                linecolor='white',
                vmin=0,
                vmax=6
            )

            cbar = ax.collections[0].colorbar
            cbar.set_ticklabels([
                '0 - Liquidated',
                '1 - Very Healthy',
                '2 - Healthy',
                '3 - Caution',
                '4 - High Risk',
                '5 - Imminent Insolvency',
                '6 - Insolvent'
            ])

            num_of_vaults = subset['num_vaults'].unique()[0]

            plt.title(f"Risk Heatmap - Scale {num_of_vaults} Vaults", pad=10)
            plt.xlabel("Price Drop")
            plt.ylabel("Overall Protocol Risk Level")
            plt.xticks(rotation=45, ha='right')
            plt.yticks(rotation=0)
            plt.tight_layout()
            plt.savefig(self.output_dir / f"risk_heatmap_{sc}.png", dpi=300)
            plt.close()

    def plot_protocol_health(self, scenario, scenario_df):
        """Plot protocol health factor evolution for a single scenario"""
        plt.figure(figsize=(12, 6))

        sns.lineplot(
            data=scenario_df,
            x='simulation_hour',
            y='protocol_health_factor',
            errorbar=None
        )

        plt.title(f'Protocol Health Factor Evolution - {scenario}')
        plt.xlabel('Simulation Hours')
        plt.ylabel('Health Factor')
        plt.grid(True)
        plt.tight_layout()

        plt.savefig(self.output_dir / scenario / 'protocol_health.png')
        plt.close()

    def plot_liquidation_metrics(self, scenario, scenario_df):
        """Plot liquidation-related metrics for a single scenario"""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

        # Liquidated vaults over time
        sns.lineplot(
            data=scenario_df,
            x='simulation_hour',
            y='num_liquidated_vaults',
            errorbar=None,
            ax=ax1,
            color='red'
        )
        ax1.set_title(f'Number of Liquidated Vaults Over Time - {scenario}')
        ax1.set_xlabel('Simulation Hours')
        ax1.set_ylabel('Number of Liquidated Vaults')
        ax1.grid(True)

        # Liquidation queue size
        sns.lineplot(
            data=scenario_df,
            x='simulation_hour',
            y='liquidation_queue_size',
            errorbar=None,
            ax=ax2,
            color='orange'
        )
        ax2.set_title(f'Liquidation Queue Size Over Time - {scenario}')
        ax2.set_xlabel('Simulation Hours')
        ax2.set_ylabel('Queue Size')
        ax2.grid(True)

        plt.tight_layout()
        plt.savefig(self.output_dir / scenario / 'liquidation_metrics.png')
        plt.close()

    def plot_collateralization_ratio(self, scenario, scenario_df):
        """Plot protocol collateralization ratio trends for a single scenario"""
        plt.figure(figsize=(12, 6))

        sns.lineplot(
            data=scenario_df,
            x='simulation_hour',
            y='collateralization_ratio',
            errorbar=None,
            color='green'
        )

        plt.title(f'Collateralization Ratio Over Time - {scenario}')
        plt.xlabel('Simulation Hours')
        plt.ylabel('Protocol Collateralization Ratio (%)')
        plt.grid(True)
        plt.tight_layout()

        plt.savefig(self.output_dir / scenario /
                    'protocol_collateralization_ratio.png')
        plt.close()

    def plot_vault_distribution(self, scenario, scenario_df):
        """Plot vault health distribution over time for a single scenario"""
        plt.figure(figsize=(12, 6))

        # Create stacked area plot
        plt.stackplot(scenario_df['simulation_hour'],
                      [scenario_df['num_healthy_vaults'],
                      scenario_df['num_at_risk_vaults'],
                      scenario_df['num_liquidatable_vaults'],
                      scenario_df['num_liquidated_vaults']],
                      labels=['Healthy', 'At Risk',
                              'Liquidatable', 'Liquidated'],
                      alpha=0.7)

        plt.title(f'Vault Distribution Over Time - {scenario}')
        plt.xlabel('Simulation Hours')
        plt.ylabel('Number of Vaults')
        plt.legend(loc='center left', bbox_to_anchor=(1, 0.5))
        plt.grid(True)
        plt.tight_layout()

        plt.savefig(self.output_dir / scenario / 'vault_distribution.png')
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
