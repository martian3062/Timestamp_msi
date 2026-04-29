import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export default function Datasets() {
  return (
    <div className="flex-1 overflow-y-auto p-8 bg-black/5">
      <div className="max-w-6xl mx-auto space-y-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight mb-2">Datasets</h1>
          <p className="text-muted-foreground">Manage WSI files, upload labels, and trigger preprocessing.</p>
        </div>
        
        <div className="grid gap-6 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Register Slides</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="border-2 border-dashed border-border rounded-lg p-12 text-center flex flex-col items-center justify-center text-muted-foreground">
                <span className="mb-2">Drag and drop WSIs or Labels CSV here</span>
                <button className="bg-primary hover:bg-primary/90 text-primary-foreground px-4 py-2 rounded-md font-medium transition-colors text-sm">
                  Browse Files
                </button>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader>
              <CardTitle>Slide Directory</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="flex justify-between items-center p-3 rounded-md bg-secondary/30 border border-border">
                    <div>
                      <div className="font-medium text-sm text-foreground">Slide_CRC_{i}0{i}</div>
                      <div className="text-xs text-muted-foreground">Patient: P10{i} | MSI-H</div>
                    </div>
                    <span className="px-2 py-1 bg-emerald-500/20 text-emerald-400 text-xs rounded-full">
                      Tiled
                    </span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
