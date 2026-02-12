import React, { createContext, useContext, useState, useCallback, useEffect } from 'react'
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

interface GraphContextType {
  selectedGraphId: string
  graphs: Graph[]
  loading: boolean
  setSelectedGraphId: (graphId: string) => void
  refreshGraphs: () => Promise<void>
  getCurrentGraph: () => Graph | undefined
}

const GraphContext = createContext<GraphContextType | undefined>(undefined)

export const GraphProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [selectedGraphId, setSelectedGraphId] = useState('')
  const [graphs, setGraphs] = useState<Graph[]>([])
  const [loading, setLoading] = useState(false)

  const refreshGraphs = useCallback(async () => {
    setLoading(true)
    try {
      const response = await listGraphs()
      if (response.status === 'success' && response.graphs) {
        setGraphs(response.graphs)
        
        // Set selected graph if not already set
        if (!selectedGraphId && response.graphs.length > 0) {
          const defaultGraph = response.graphs.find((g: Graph) => g.is_default)
          const graphToSelect = defaultGraph || response.graphs[0]
          setSelectedGraphId(graphToSelect.id)
        }
      }
    } catch (error) {
      console.error('Failed to fetch graphs:', error)
    } finally {
      setLoading(false)
    }
  }, [])

  // Initialize graphs on mount
  useEffect(() => {
    refreshGraphs()
  }, [refreshGraphs])

  const getCurrentGraph = useCallback(() => {
    return graphs.find(g => g.id === selectedGraphId)
  }, [graphs, selectedGraphId])

  const value: GraphContextType = {
    selectedGraphId,
    graphs,
    loading,
    setSelectedGraphId,
    refreshGraphs,
    getCurrentGraph
  }

  return (
    <GraphContext.Provider value={value}>
      {children}
    </GraphContext.Provider>
  )
}

export const useGraph = () => {
  const context = useContext(GraphContext)
  if (!context) {
    throw new Error('useGraph must be used within GraphProvider')
  }
  return context
}
