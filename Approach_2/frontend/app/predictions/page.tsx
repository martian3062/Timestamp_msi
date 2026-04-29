"use client"
import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export default function Predictions() {
  const [slideId, setSlideId] = useState('')
  const [modelVersion, setModelVersion] = useState('')
  const [loading, setLoading] = useState(false)
  
  const [result, setResult] = useState<{
    prediction: string, 
    probability: number, 
    heatmap_path?: string, 
    error?: string
  } | null>(null)

  const handlePredict = async () => {
    if(!slideId || !modelVersion) return;
    setLoading(true)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080"
      const res = await fetch(`${apiUrl}/pipeline/predict`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          slide_id: slideId,
          model_version: modelVersion
        })
      });
      const data = await res.json()
      setResult(data)
    } catch (err) {
      console.error(err)
      setResult({ prediction: "Error", probability: 0, error: "Network Error" })
    } finally {
      setLoading(false)
    }
  }

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080"

  return (
    <div className="flex-1 overflow-y-auto p-8 bg-black/5">
      <div className="max-w-6xl mx-auto space-y-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight mb-2">Inference & Explainability</h1>
          <p className="text-muted-foreground">Run models on single slides and view attention heatmaps.</p>
        </div>
        
        <div className="grid gap-6 md:grid-cols-3">
          <div className="col-span-1 space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Select Target</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <input 
                  type="text" 
                  value={slideId}
                  onChange={(e) => setSlideId(e.target.value)}
                  placeholder="Enter Slide ID (e.g. TCGA-AA-3655)" 
                  className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm text-foreground"
                />
                <input 
                  type="text" 
                  value={modelVersion}
                  onChange={(e) => setModelVersion(e.target.value)}
                  placeholder="Enter Model Version/ID" 
                  className="w-full bg-background border border-border rounded-md px-3 py-2 text-sm text-foreground"
                />
                <button 
                  onClick={handlePredict} 
                  disabled={loading}
                  className="w-full bg-primary hover:bg-primary/90 text-primary-foreground px-4 py-2 rounded-md font-medium transition-colors text-sm disabled:opacity-50">
                  {loading ? "Running..." : "Run Prediction"}
                </button>
              </CardContent>
            </Card>

            {result && (
              <Card className="border-emerald-500/30 bg-emerald-500/5 text-emerald-500">
                <CardContent className="p-6">
                  <div className="text-sm font-medium mb-1 line-clamp-1">Result: {slideId}</div>
                  <div className="text-4xl font-bold mb-2">{result.prediction}</div>
                  <div className="text-sm opacity-80">Confidence: {(result.probability * 100).toFixed(1)}%</div>
                  {result.error && <div className="text-xs text-red-500 mt-2">{result.error}</div>}
                </CardContent>
              </Card>
            )}
          </div>
          
          <div className="col-span-2">
            <Card className="h-full min-h-[500px] flex flex-col">
              <CardHeader>
                <CardTitle>Attention Heatmap</CardTitle>
              </CardHeader>
              <CardContent className="flex-1 flex items-center justify-center bg-black/20 m-6 mt-0 rounded-md border border-border overflow-hidden relative">
                {loading ? (
                    <div className="text-muted-foreground animate-pulse text-sm">Generating Heatmap...</div>
                ) : result?.heatmap_path ? (
                    <img 
                      src={result.heatmap_path.startsWith('http') ? result.heatmap_path : `${apiUrl}${result.heatmap_path}`} 
                      alt="Heatmap Visualization" 
                      className="object-contain w-full h-full"
                    />
                ) : (
                    <div className="text-muted-foreground flex flex-col items-center">
                      <svg className="w-12 h-12 mb-4 opacity-20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                      </svg>
                      <span>Heatmap visualization</span>
                      <span className="text-xs mt-2 opacity-50">Requires inference to be completed</span>
                    </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}
