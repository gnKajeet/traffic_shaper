#!/usr/bin/env python3
"""
Traffic Shaping Policy Results Visualization
Generates charts from policy_test_results.csv
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import sys
from pathlib import Path

# Set style
sns.set_theme(style="whitegrid")
plt.rcParams['figure.figsize'] = (14, 10)

def load_data(csv_file):
    """Load and prepare the CSV data"""
    try:
        df = pd.read_csv(csv_file)
        print(f"Loaded {len(df)} policy test results from {csv_file}")
        print(f"Columns: {', '.join(df.columns)}")
        return df
    except FileNotFoundError:
        print(f"Error: File '{csv_file}' not found!")
        print("Please run: scp root@137.184.194.112:/root/traffic_shaper/policy_test_results.csv .")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading CSV: {e}")
        sys.exit(1)

def create_plots(df, output_prefix='policy_results'):
    """Create visualizations of the test results"""

    # Filter out error rows
    df_clean = df[df['Bitrate_Sender_Mbps'] != 'ERROR'].copy()
    df_clean = df_clean[df_clean['Bitrate_Sender_Mbps'] != 'N/A'].copy()

    # Convert to numeric
    numeric_cols = ['Bitrate_Sender_Mbps', 'Bitrate_Receiver_Mbps',
                    'Transfer_Sender_MB', 'Transfer_Receiver_MB', 'Retransmissions']
    for col in numeric_cols:
        df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')

    print(f"\nProcessing {len(df_clean)} valid test results")

    # Create figure with subplots
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Traffic Shaping Policy Performance Analysis', fontsize=16, fontweight='bold')

    # Plot 1: Bitrate Comparison (Sender vs Receiver)
    ax1 = axes[0, 0]
    x = range(len(df_clean))
    width = 0.35
    ax1.bar([i - width/2 for i in x], df_clean['Bitrate_Sender_Mbps'],
            width, label='Sender', alpha=0.8, color='steelblue')
    ax1.bar([i + width/2 for i in x], df_clean['Bitrate_Receiver_Mbps'],
            width, label='Receiver', alpha=0.8, color='coral')
    ax1.set_xlabel('Policy', fontweight='bold')
    ax1.set_ylabel('Bitrate (Mbps)', fontweight='bold')
    ax1.set_title('Bitrate: Sender vs Receiver', fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(df_clean['Policy'], rotation=45, ha='right')
    ax1.legend()
    ax1.grid(axis='y', alpha=0.3)

    # Plot 2: Transfer Volume
    ax2 = axes[0, 1]
    ax2.bar([i - width/2 for i in x], df_clean['Transfer_Sender_MB'],
            width, label='Sender', alpha=0.8, color='green')
    ax2.bar([i + width/2 for i in x], df_clean['Transfer_Receiver_MB'],
            width, label='Receiver', alpha=0.8, color='lightgreen')
    ax2.set_xlabel('Policy', fontweight='bold')
    ax2.set_ylabel('Transfer (MB)', fontweight='bold')
    ax2.set_title('Data Transfer Volume (10 second test)', fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels(df_clean['Policy'], rotation=45, ha='right')
    ax2.legend()
    ax2.grid(axis='y', alpha=0.3)

    # Plot 3: Retransmissions
    ax3 = axes[1, 0]
    bars = ax3.bar(x, df_clean['Retransmissions'], color='crimson', alpha=0.7)
    ax3.set_xlabel('Policy', fontweight='bold')
    ax3.set_ylabel('Retransmissions', fontweight='bold')
    ax3.set_title('TCP Retransmissions (Packet Loss Indicator)', fontweight='bold')
    ax3.set_xticks(x)
    ax3.set_xticklabels(df_clean['Policy'], rotation=45, ha='right')
    ax3.grid(axis='y', alpha=0.3)

    # Add value labels on retransmission bars
    for i, bar in enumerate(bars):
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height)}',
                ha='center', va='bottom', fontsize=9)

    # Plot 4: Efficiency (Receiver/Sender ratio)
    ax4 = axes[1, 1]
    efficiency = (df_clean['Bitrate_Receiver_Mbps'] / df_clean['Bitrate_Sender_Mbps'] * 100).fillna(0)
    bars = ax4.bar(x, efficiency, color='purple', alpha=0.7)
    ax4.set_xlabel('Policy', fontweight='bold')
    ax4.set_ylabel('Efficiency (%)', fontweight='bold')
    ax4.set_title('Transfer Efficiency (Receiver/Sender %)', fontweight='bold')
    ax4.set_xticks(x)
    ax4.set_xticklabels(df_clean['Policy'], rotation=45, ha='right')
    ax4.axhline(y=100, color='green', linestyle='--', alpha=0.5, label='100% (ideal)')
    ax4.legend()
    ax4.grid(axis='y', alpha=0.3)
    ax4.set_ylim(0, 110)

    # Add value labels
    for i, bar in enumerate(bars):
        height = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}%',
                ha='center', va='bottom', fontsize=8)

    plt.tight_layout()

    # Save plot
    output_file = f'{output_prefix}_overview.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n✓ Saved overview plot: {output_file}")

    # Create second figure: Average RTT if available
    if 'Avg_RTT_ms' in df_clean.columns:
        df_rtt = df_clean[df_clean['Avg_RTT_ms'] != 'N/A'].copy()
        if not df_rtt.empty:
            df_rtt['Avg_RTT_ms'] = pd.to_numeric(df_rtt['Avg_RTT_ms'], errors='coerce')

            fig2, ax = plt.subplots(figsize=(12, 6))
            bars = ax.bar(range(len(df_rtt)), df_rtt['Avg_RTT_ms'],
                         color='orange', alpha=0.7)
            ax.set_xlabel('Policy', fontweight='bold')
            ax.set_ylabel('Average RTT (ms)', fontweight='bold')
            ax.set_title('Average Round Trip Time by Policy', fontweight='bold')
            ax.set_xticks(range(len(df_rtt)))
            ax.set_xticklabels(df_rtt['Policy'], rotation=45, ha='right')
            ax.grid(axis='y', alpha=0.3)

            # Add value labels
            for i, bar in enumerate(bars):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.0f}',
                       ha='center', va='bottom', fontsize=9)

            plt.tight_layout()
            rtt_file = f'{output_prefix}_rtt.png'
            plt.savefig(rtt_file, dpi=300, bbox_inches='tight')
            print(f"✓ Saved RTT plot: {rtt_file}")

    # Create comparison table
    fig3, ax = plt.subplots(figsize=(14, 8))
    ax.axis('tight')
    ax.axis('off')

    # Prepare table data
    table_data = df_clean[['Policy', 'Bitrate_Sender_Mbps', 'Bitrate_Receiver_Mbps',
                           'Transfer_Sender_MB', 'Transfer_Receiver_MB', 'Retransmissions']].copy()
    table_data.columns = ['Policy', 'Bitrate\nSender\n(Mbps)', 'Bitrate\nReceiver\n(Mbps)',
                          'Transfer\nSender\n(MB)', 'Transfer\nReceiver\n(MB)', 'Retrans-\nmissions']

    # Format numbers
    for col in table_data.columns[1:]:
        if col == 'Retrans-\nmissions':
            table_data[col] = table_data[col].apply(lambda x: f'{int(x)}')
        else:
            table_data[col] = table_data[col].apply(lambda x: f'{x:.2f}')

    table = ax.table(cellText=table_data.values, colLabels=table_data.columns,
                    cellLoc='center', loc='center', bbox=[0, 0, 1, 1])
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 2)

    # Style header
    for i in range(len(table_data.columns)):
        table[(0, i)].set_facecolor('#4472C4')
        table[(0, i)].set_text_props(weight='bold', color='white')

    # Alternate row colors
    for i in range(1, len(table_data) + 1):
        for j in range(len(table_data.columns)):
            if i % 2 == 0:
                table[(i, j)].set_facecolor('#E7E6E6')
            else:
                table[(i, j)].set_facecolor('white')

    plt.title('Traffic Shaping Policy Test Results Summary',
              fontsize=14, fontweight='bold', pad=20)

    table_file = f'{output_prefix}_table.png'
    plt.savefig(table_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved table: {table_file}")

def print_summary(df):
    """Print summary statistics"""
    df_clean = df[df['Bitrate_Sender_Mbps'] != 'ERROR'].copy()
    df_clean = df_clean[df_clean['Bitrate_Sender_Mbps'] != 'N/A'].copy()

    numeric_cols = ['Bitrate_Sender_Mbps', 'Bitrate_Receiver_Mbps',
                    'Transfer_Sender_MB', 'Transfer_Receiver_MB', 'Retransmissions']
    for col in numeric_cols:
        df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')

    print("\n" + "="*60)
    print("SUMMARY STATISTICS")
    print("="*60)
    print(f"\nFastest Policy (Receiver Bitrate):")
    fastest = df_clean.loc[df_clean['Bitrate_Receiver_Mbps'].idxmax()]
    print(f"  {fastest['Policy']}: {fastest['Bitrate_Receiver_Mbps']:.2f} Mbps")

    print(f"\nSlowest Policy (Receiver Bitrate):")
    slowest = df_clean.loc[df_clean['Bitrate_Receiver_Mbps'].idxmin()]
    print(f"  {slowest['Policy']}: {slowest['Bitrate_Receiver_Mbps']:.2f} Mbps")

    print(f"\nMost Retransmissions:")
    most_retrans = df_clean.loc[df_clean['Retransmissions'].idxmax()]
    print(f"  {most_retrans['Policy']}: {int(most_retrans['Retransmissions'])} retransmissions")

    print(f"\nBest Efficiency (Receiver/Sender):")
    df_clean['Efficiency'] = (df_clean['Bitrate_Receiver_Mbps'] / df_clean['Bitrate_Sender_Mbps'] * 100)
    best_eff = df_clean.loc[df_clean['Efficiency'].idxmax()]
    print(f"  {best_eff['Policy']}: {best_eff['Efficiency']:.2f}%")

    print("\n" + "="*60)

def main():
    """Main function"""
    # Check for CSV file
    csv_file = 'policy_test_results.csv'
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]

    print("Traffic Shaping Policy Results Visualization")
    print("=" * 60)

    # Load data
    df = load_data(csv_file)

    # Create plots
    create_plots(df)

    # Print summary
    print_summary(df)

    print("\n✓ Visualization complete!")
    print("\nGenerated files:")
    print("  - policy_results_overview.png  (4 charts)")
    print("  - policy_results_rtt.png       (RTT chart)")
    print("  - policy_results_table.png     (Summary table)")

if __name__ == '__main__':
    main()
