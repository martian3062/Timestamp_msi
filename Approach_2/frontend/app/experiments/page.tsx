"use client"
import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

interface Experiment {
  id: number
  experiment_id: string
  name: string
  status: string
  model_type: string
  metrics?: any
  created_at: string
}

export default function Experiments() {
  const [experiments, setExperiments] = useState<Experiment[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedExp, setSelectedExp] = useState<Experiment | null>(null)
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080"

  useEffect(() => {
    fetchExperiments()
  }, [])

  const fetchExperiments = async () => {
    try {
      setLoading(true)
      const res = await fetch(`${apiUrl}/experiments/`)
      const data = await res.json()
      setExperiments(Array.isArray(data) ? data : [])
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const renderMetricsImages = (exp: Experiment) => {
    if (!exp.metrics) return <div className="p-4 text-sm text-muted-foreground">No metrics yet</div>
    let metricsData = exp.metrics;
    if (typeof metricsData === 'string') {
        try { metricsData = JSON.parse(metricsData) } catch(e) {}
    }
    
    return (
        <div className="grid grid-cols-2 gap-4 mt-6">
            {metricsData.roc_curve && (
                <div className="space-y-2">
                    <h4 className="text-sm font-medium text-foreground">ROC Curve</h4>
                    <div className="border border-border rounded bg-black/20 p-2">
                        <img src={`${apiUrl}${metricsData.roc_curve}`} alt="ROC" className="max-w-full rounded" />
                    </div>
                </div>
            )}
            {metricsData.pr_curve && (
                <div className="space-y-2">
                    <h4 className="text-sm font-medium text-foreground">PR Curve</h4>
                    <div className="border border-border rounded bg-black/20 p-2">
                        <img src={`${apiUrl}${metricsData.pr_curve}`} alt="PR Curve" className="max-w-full rounded" />
                    </div>
                </div>
            )}
        </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto p-8 bg-black/5">
        <div className="max-w-6xl mx-auto space-y-8">
            <div className="flex justify-between items-end">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight mb-2">Model Registry & Experiments</h1>
                    <p className="text-muted-foreground">Compare training runs synced from MLflow via slideflow metrics.</p>
                </div>
                <button onClick={fetchExperiments} className="bg-secondary hover:bg-secondary/80 text-foreground px-4 py-2 rounded-md font-medium transition-colors text-sm border border-border">
                    {loading ? "Syncing..." : "Sync from DB"}
                </button>
            </div>
            
            <Card>
                <CardHeader>
                    <CardTitle>Experiment Registry</CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="w-full relative overflow-x-auto rounded-md border border-border">
                        <table className="w-full text-sm text-left">
                            <thead className="text-xs text-muted-foreground bg-secondary/50 uppercase border-b border-border">
                                <tr>
                                    <th className="px-6 py-4 font-medium">Model ID</th>
                                    <th className="px-6 py-4 font-medium">Type</th>
                                    <th className="px-6 py-4 font-medium">Status</th>
                                    <th className="px-6 py-4 font-medium text-right">Action</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-border">
                                {experiments.map((exp) => (
                                    <tr key={exp.experiment_id} className="bg-background/40 hover:bg-muted/10 transition-colors">
                                        <td className="px-6 py-4 whitespace-nowrap font-medium text-primary">{exp.experiment_id} ({exp.name})</td>
                                        <td className="px-6 py-4 whitespace-nowrap">{exp.model_type}</td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className={`px-2 py-1 text-xs rounded-full ${exp.status === 'completed' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-blue-500/20 text-blue-400'}`}>
                                                {exp.status}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-right">
                                            <button onClick={() => setSelectedExp(selectedExp?.id === exp.id ? null : exp)} className="text-primary hover:text-primary/80 transition-colors">
                                                {selectedExp?.id === exp.id ? "Hide Metrics" : "View Metrics"}
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                                {experiments.length === 0 && !loading && (
                                    <tr><td colSpan={4} className="text-center py-6 text-muted-foreground">No experiments found.</td></tr>
                                )}
                            </tbody>
                        </table>
                    </div>

                    {selectedExp && renderMetricsImages(selectedExp)}
                </CardContent>
            </Card>
        </div>
    </div>
  )
}
