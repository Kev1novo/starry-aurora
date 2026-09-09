import client from './client'

export interface SchemaField {
  id: number
  table_name: string
  column_name: string
  data_type: string
  description?: string
  column_comment?: string
  is_primary_key: boolean
}

export async function getSchemaFields(datasourceId: number): Promise<SchemaField[]> {
  const res = await client.get(`/datasources/${datasourceId}/schemas`)
  return res.data.data || []
}