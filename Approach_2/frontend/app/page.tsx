import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export default function Home() {
  return (
    <div className="flex-1 overflow-y-auto p-8 bg-black/5">
      <div className="max-w-6xl mx-auto space-y-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight mb-2">Platform Overview</h1>
          <p className="text-muted-foreground">Monitor your MSI inference pipeline and models.</p>
        </div>

        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
          <Card className="bg-gradient-to-br from-card to-card/50 border-primary/20 transition-all hover:border-primary/50">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Total Slides</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-primary">1,248</div>
            </CardContent>
          </Card>
          <Card className="bg-gradient-to-br from-card to-card/50 transition-all hover:bg-card/80">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Active Experiments</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold">3</div>
            </CardContent>
          </Card>
          <Card className="bg-gradient-to-br from-card to-card/50 transition-all hover:bg-card/80">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Best Validation AUC</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-emerald-500">0.892</div>
            </CardContent>
          </Card>
          <Card className="bg-gradient-to-br from-card to-card/50 transition-all hover:bg-card/80">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">Pending Inferences</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-orange-400">12</div>
            </CardContent>
          </Card>
        </div>

        <div className="grid gap-6 md:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>Recent Activity</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center gap-4 text-sm">
                  <div className="w-2 h-2 rounded-full bg-emerald-500" />
                  <div className="flex-1">Experiment <b>Attention_MIL_v2</b> completed</div>
                  <div className="text-muted-foreground text-xs">2 hours ago</div>
                </div>
                <div className="flex items-center gap-4 text-sm">
                  <div className="w-2 h-2 rounded-full bg-blue-500" />
                  <div className="flex-1">Preprocessing finished for cohort <b>TCGA-CRC</b></div>
                  <div className="text-muted-foreground text-xs">5 hours ago</div>
                </div>
                <div className="flex items-center gap-4 text-sm">
                  <div className="w-2 h-2 rounded-full bg-purple-500" />
                  <div className="flex-1">Features extracted using <b>ResNet50</b></div>
                  <div className="text-muted-foreground text-xs">Yesterday</div>
                </div>
              </div>
            </CardContent>
          </Card>
          
          <Card>
            <CardHeader>
              <CardTitle>Quick Actions</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              <a href="/datasets" className="w-full text-left px-4 py-3 rounded-md bg-secondary/50 hover:bg-secondary transition-colors text-sm font-medium border border-border">
                Register New Slides
              </a>
              <a href="/training" className="w-full text-left px-4 py-3 rounded-md bg-secondary/50 hover:bg-secondary transition-colors text-sm font-medium border border-border">
                Start MIL Training
              </a>
              <a href="/predictions" className="w-full text-left px-4 py-3 rounded-md bg-primary/20 text-primary hover:bg-primary/30 transition-colors text-sm font-medium border border-primary/20">
                Run Inference
              </a>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
