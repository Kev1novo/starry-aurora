import React from 'react';
import { Table } from 'antd';
import type { ColumnsType } from 'antd/es/table';

interface PaginationInfo {
  current: number;
  pageSize: number;
  total: number;
}

interface DataTableProps {
  columns: ColumnsType<any>;
  dataSource: any[];
  loading?: boolean;
  pagination?: PaginationInfo | false;
  onChange?: (page: number, pageSize: number) => void;
  scroll?: { x?: number; y?: number };
  rowKey?: string;
}

const defaultPagination: PaginationInfo = {
  current: 1,
  pageSize: 10,
  total: 0,
};

const DataTable: React.FC<DataTableProps> = ({
  columns,
  dataSource,
  loading = false,
  pagination = defaultPagination,
  onChange,
  scroll = { x: 800 },
  rowKey = 'id',
}) => {
  const handleTableChange = (pag: { current: number; pageSize: number }): void => {
    onChange?.(pag.current, pag.pageSize);
  };

  const paginationConfig =
    pagination === false
      ? false
      : {
          ...defaultPagination,
          ...pagination,
          showSizeChanger: true,
          showQuickJumper: true,
          pageSizeOptions: [10, 20, 50, 100],
          locale: {
            items_per_page: '条/页',
          },
        };

  return (
    <Table
      columns={columns}
      dataSource={dataSource}
      loading={loading}
      pagination={paginationConfig}
      onChange={handleTableChange as any}
      scroll={scroll}
      rowKey={rowKey}
      locale={{
        emptyText: '暂无数据',
      }}
    />
  );
};

export default DataTable;