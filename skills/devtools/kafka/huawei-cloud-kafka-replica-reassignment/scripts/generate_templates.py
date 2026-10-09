#!/usr/bin/env python3
"""
Generate template xlsx files for topic and broker.

Creates blank templates with correct headers and sample data rows
that users can fill in and upload.

Note (version A): the broker template keeps the production Chinese-language headers
(the same column names the runtime reads and writes) because the tool's runtime language
is Chinese; Version B ships an English-header template.
"""

import os
import openpyxl


def generate_topic_template(output_path):
    """Generate topic_template.xlsx with headers and sample data."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Topic'

    headers = ['Topic', 'PartitionCount', 'Partition', 'Broker ID', 'Path',
               'Size(bytes)', 'Size(GB)']
    ws.append(headers)

    # Sample data (3 topics with partitions)
    samples = [
        # Topic 1: 6 partitions
        ('ITDE_DEV_rfr_channel_ifrs_lkp', 6, 0, 6, '/srv/BigData/data1', 107374182, 0.1),
        ('ITDE_DEV_rfr_channel_ifrs_lkp', 6, 1, 7, '/srv/BigData/data1', 214748365, 0.2),
        ('ITDE_DEV_rfr_channel_ifrs_lkp', 6, 2, 5, '/srv/BigData/data1', 322122547, 0.3),
        ('ITDE_DEV_rfr_channel_ifrs_lkp', 6, 3, 10, '/srv/BigData/data1', 429496730, 0.4),
        ('ITDE_DEV_rfr_channel_ifrs_lkp', 6, 4, 15, '/srv/BigData/data1', 536870912, 0.5),
        ('ITDE_DEV_rfr_channel_ifrs_lkp', 6, 5, 9, '/srv/BigData/data1', 644245094, 0.6),
        # Topic 2: 10 partitions
        ('ITDE_PROD_StoIndihome_lkp', 10, 0, 16, '/srv/BigData/data4', 0, 0),
        ('ITDE_PROD_StoIndihome_lkp', 10, 1, 13, '/srv/BigData/data5', 0, 0),
        ('ITDE_PROD_StoIndihome_lkp', 10, 2, 2, '/srv/BigData/data4', 0, 0),
        ('ITDE_PROD_StoIndihome_lkp', 10, 3, 8, '/srv/BigData/data3', 0, 0),
        ('ITDE_PROD_StoIndihome_lkp', 10, 4, 12, '/srv/BigData/data3', 0, 0),
        ('ITDE_PROD_StoIndihome_lkp', 10, 5, 14, '/srv/BigData/data4', 0, 0),
        ('ITDE_PROD_StoIndihome_lkp', 10, 6, 1, '/srv/BigData/data3', 0, 0),
        ('ITDE_PROD_StoIndihome_lkp', 10, 7, 6, '/srv/BigData/data6', 0, 0),
        ('ITDE_PROD_StoIndihome_lkp', 10, 8, 7, '/srv/BigData/data2', 0, 0),
        ('ITDE_PROD_StoIndihome_lkp', 10, 9, 5, '/srv/BigData/data6', 0, 0),
        # Topic 3: 6 partitions with larger data
        ('ITDE_PROD_ad_dim_lkp', 6, 0, 6, '/srv/BigData/data4', 107374182, 0.1),
        ('ITDE_PROD_ad_dim_lkp', 6, 1, 7, '/srv/BigData/data4', 118111601, 0.11),
        ('ITDE_PROD_ad_dim_lkp', 6, 2, 5, '/srv/BigData/data2', 128849019, 0.12),
        ('ITDE_PROD_ad_dim_lkp', 6, 3, 10, '/srv/BigData/data4', 139586437, 0.13),
        ('ITDE_PROD_ad_dim_lkp', 6, 4, 15, '/srv/BigData/data1', 150323855, 0.14),
        ('ITDE_PROD_ad_dim_lkp', 6, 5, 9, '/srv/BigData/data1', 161061274, 0.15),
    ]

    for row in samples:
        ws.append(row)

    # Style header row
    for cell in ws[1]:
        cell.font = openpyxl.styles.Font(bold=True, color='FFFFFF')
        cell.fill = openpyxl.styles.PatternFill(start_color='3498DB', end_color='3498DB', fill_type='solid')
        cell.alignment = openpyxl.styles.Alignment(horizontal='center')

    # Auto-width columns
    for i, col in enumerate(ws.columns, 1):
        max_len = max(len(str(cell.value or '')) for cell in col)
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = max_len + 3

    wb.save(output_path)
    return output_path


def generate_broker_template(output_path):
    """Generate broker_template.xlsx with headers and sample data."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Broker'

    # Version A: Chinese headers, consistent with the Chinese runtime language.
    headers = ['Broker ID', 'Host', 'Disk (Used | Total)', '分区', '挂载点',
               '已使用（GB）', '磁盘大小（GB）', '磁盘使用率']
    ws.append(headers)

    # Sample: 16 brokers, each with 5 mountpoints
    brokers = []
    for bid in range(1, 17):
        host = f'10.51.128.{165 + bid - 1}'
        for midx, (dev, mnt) in enumerate([
            ('/dev/vdb1', '/srv/BigData/data1'),
            ('/dev/vdc1', '/srv/BigData/data2'),
            ('/dev/vdd1', '/srv/BigData/data3'),
            ('/dev/vde1', '/srv/BigData/data4'),
            ('/dev/vdg1', '/srv/BigData/data6'),
        ]):
            # Simulate varied usage
            base_used = 250 + (bid * 7 + midx * 15) % 100
            total = 922.21
            usage = round(base_used / total * 100, 2)
            brokers.append((bid, host, '1.8TB | 5.4TB', dev, mnt, base_used, total, usage))

    for row in brokers:
        ws.append(row)

    # Style header row
    for cell in ws[1]:
        cell.font = openpyxl.styles.Font(bold=True, color='FFFFFF')
        cell.fill = openpyxl.styles.PatternFill(start_color='3498DB', end_color='3498DB', fill_type='solid')
        cell.alignment = openpyxl.styles.Alignment(horizontal='center')

    # Format usage column as percentage-like
    for row in ws.iter_rows(min_row=2):
        row[7].number_format = '0.00'

    # Auto-width columns
    for i, col in enumerate(ws.columns, 1):
        max_len = max(len(str(cell.value or '')) for cell in col)
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = max_len + 3

    wb.save(output_path)
    return output_path


def generate_all_templates(output_dir):
    """Generate both templates."""
    os.makedirs(output_dir, exist_ok=True)
    topic_path = os.path.join(output_dir, 'topic_template.xlsx')
    broker_path = os.path.join(output_dir, 'broker_template.xlsx')
    generate_topic_template(topic_path)
    generate_broker_template(broker_path)
    return topic_path, broker_path


if __name__ == '__main__':
    import sys
    output_dir = sys.argv[1] if len(sys.argv) > 1 else '.'
    topic, broker = generate_all_templates(output_dir)
    print(f'Templates generated:')
    print(f'  Topic: {topic}')
    print(f'  Broker: {broker}')