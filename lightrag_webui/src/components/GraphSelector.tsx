import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { RotateCw, Plus, Settings2 } from 'lucide-react'
import Button from '@/components/ui/Button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/Select'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { toast } from 'sonner'
import { listGraphs } from '@/api/lightrag'

interface Graph {
  id: string
  name: string
  description: string
  created_at: string
  updated_at: string
  document_count: number
  entity_count: number
  relation_count: number
  is_default?: boolean
}

interface GraphSelectorProps {
  selectedGraphId?: string
  onGraphSelect?: (graphId: string) => void
  compact?: boolean
}

export default function GraphSelector({
  selectedGraphId = '',
  onGraphSelect,
  compact = false
}: GraphSelectorProps) {
  const { t } = useTranslation()
  const [graphs, setGraphs] = useState<Graph[]>([])
  const [loading, setLoading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [selectedId, setSelectedId] = useState(selectedGraphId)

  // Fetch graphs on mount
  useEffect(() => {
    fetchGraphs()
  }, [])

  // Update local state when parent selectedGraphId changes
  useEffect(() => {
    if (selectedGraphId && selectedGraphId !== selectedId) {
      setSelectedId(selectedGraphId)
    }
  }, [selectedGraphId])

  const fetchGraphs = async () => {
    setLoading(true)
    try {
      const response = await listGraphs()
      if (response.status === 'success' && response.graphs) {
        setGraphs(response.graphs)
        
        // If no graph is selected, select the first one or default
        if (!selectedId && response.graphs.length > 0) {
          const defaultGraph = response.graphs.find((g: Graph) => g.is_default)
          const graphToSelect = defaultGraph || response.graphs[0]
          setSelectedId(graphToSelect.id)
          onGraphSelect?.(graphToSelect.id)
        }
      } else {
        // Handle empty or error response
        setGraphs([])
      }
    } catch (error) {
      console.error('Error fetching graphs:', error)
      toast.error(t('error.failedToFetchGraphs'))
      setGraphs([])
    } finally {
      setLoading(false)
    }
  }

  const handleRefresh = useCallback(async () => {
    setRefreshing(true)
    try {
      await fetchGraphs()
      toast.success(t('graphSelector.refreshed'))
    } finally {
      setRefreshing(false)
    }
  }, [t])

  const handleGraphSelect = (graphId: string) => {
    setSelectedId(graphId)
    onGraphSelect?.(graphId)
  }

  if (compact) {
    return (
      <div className="flex items-center gap-2">
        <Select value={selectedId} onValueChange={handleGraphSelect} disabled={loading}>
          <SelectTrigger className="w-full">
            <SelectValue placeholder={t('graphSelector.selectGraph')} />
          </SelectTrigger>
          <SelectContent>
            {graphs.map((graph) => (
              <SelectItem key={graph.id} value={graph.id}>
                <span className="flex items-center gap-2">
                  {graph.name}
                  {graph.is_default && <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">default</span>}
                </span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button
          variant="outline"
          size="sm"
          onClick={handleRefresh}
          disabled={refreshing || loading}
        >
          <RotateCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
        </Button>
      </div>
    )
  }

  const selectedGraph = graphs.find(g => g.id === selectedId)

  return (
    <Card className="w-full">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">{t('graphSelector.title')}</CardTitle>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleRefresh}
            disabled={refreshing || loading}
          >
            <RotateCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Graph Selection */}
        <div className="space-y-2">
          <label className="text-sm font-medium">{t('graphSelector.selectGraph')}</label>
          <Select value={selectedId} onValueChange={handleGraphSelect} disabled={loading}>
            <SelectTrigger>
              <SelectValue placeholder={t('graphSelector.selectGraph')} />
            </SelectTrigger>
            <SelectContent>
              {graphs.map((graph) => (
                <SelectItem key={graph.id} value={graph.id}>
                  <div className="flex items-center gap-2">
                    <span>{graph.name}</span>
                    {graph.is_default && (
                      <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                        default
                      </span>
                    )}
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Selected Graph Details */}
        {selectedGraph && (
          <div className="bg-gray-50 dark:bg-gray-900 p-3 rounded-md space-y-2 text-sm">
            <div className="font-semibold">{selectedGraph.name}</div>
            {selectedGraph.description && (
              <div className="text-gray-600 dark:text-gray-400">{selectedGraph.description}</div>
            )}
            <div className="grid grid-cols-3 gap-2 pt-2 border-t border-gray-200 dark:border-gray-700">
              <div>
                <div className="text-gray-500 dark:text-gray-400">{t('graphSelector.documents')}</div>
                <div className="font-semibold">{selectedGraph.document_count}</div>
              </div>
              <div>
                <div className="text-gray-500 dark:text-gray-400">{t('graphSelector.entities')}</div>
                <div className="font-semibold">{selectedGraph.entity_count}</div>
              </div>
              <div>
                <div className="text-gray-500 dark:text-gray-400">{t('graphSelector.relations')}</div>
                <div className="font-semibold">{selectedGraph.relation_count}</div>
              </div>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-2 pt-2 border-t border-gray-200 dark:border-gray-700">
          <Button size="sm" variant="outline" className="flex-1">
            <Plus className="w-4 h-4 mr-2" />
            {t('graphSelector.createNew')}
          </Button>
          <Button size="sm" variant="outline" className="flex-1">
            <Settings2 className="w-4 h-4 mr-2" />
            {t('graphSelector.settings')}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
