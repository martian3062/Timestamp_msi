import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export default function Training() {
  return (
    <div className="flex-1 overflow-y-auto p-8 bg-black/5">
      <div className="max-w-6xl mx-auto space-y-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight mb-2">MIL Training</h1>
          <p className="text-muted-foreground">Configure and start Multiple Instance Learning models with Slideflow.</p>
        </div>
        
        <Card>
          <CardHeader>
            <CardTitle>New Training Run</CardTitle>
          </CardHeader>
          <CardContent>
            <form className="space-y-6 max-w-2xl">
              <div className="grid gap-2">
                <label className="text-sm font-medium">Experiment Name</label>
                <input type="text" className="bg-background border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary" placeholder="e.g. TCGA_ResNet_AttentionMIL" />
              </div>
              <div className="grid gap-2">
                <label className="text-sm font-medium">Model Architecture</label>
                <select className="bg-background border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary">
                  <option>Attention MIL</option>
                  <option>CLAM-SB</option>
                  <option>TransMIL</option>
                </select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="grid gap-2">
                  <label className="text-sm font-medium">Epochs</label>
                  <input type="number" defaultValue={10} className="bg-background border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary" />
                </div>
                <div className="grid gap-2">
                  <label className="text-sm font-medium">Batch Size</label>
                  <input type="number" defaultValue={32} className="bg-background border border-border rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary" />
                </div>
              </div>
              <button type="button" className="bg-primary hover:bg-primary/90 text-primary-foreground px-4 py-2 rounded-md font-medium transition-colors text-sm w-full">
                Initialize Background Training Job
              </button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
