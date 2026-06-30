import Link from "next/link";
import { Search, Plane, ArrowRight, Brain } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export default function HomePage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[calc(100vh-4rem)] p-4 md:p-8">
      <div className="max-w-4xl w-full space-y-10">
        {/* Hero */}
        <div className="text-center space-y-4">
          <div className="flex items-center justify-center gap-2">
            <Brain className="h-10 w-10 text-primary" />
            <h1 className="text-4xl font-bold tracking-tight">AI Coursework Lab</h1>
          </div>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            基于统一技术底座的智能应用系统设计课设作品集。
            探索两种不同的 AI Agent 范式，体验智能知识问答与多 Agent 协同规划。
          </p>
        </div>

        {/* Cards */}
        <div className="grid gap-6 md:grid-cols-2">
          {/* KnowSeeker Card */}
          <Card className="group relative overflow-hidden border-2 transition-all hover:border-primary/50 hover:shadow-lg">
            <CardHeader className="pb-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                  <Search className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <CardTitle className="text-xl">KnowSeeker</CardTitle>
                  <CardDescription>Agentic RAG 知识助手</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-muted-foreground">
                单 Agent 深度推理 — 上传文档构建知识库，
                AI 自主分析问题并制定多轮检索策略，生成带引用的精准回答。
              </p>
              <div className="flex flex-wrap gap-2">
                <Badge variant="secondary">Agentic RAG</Badge>
                <Badge variant="secondary">向量检索</Badge>
                <Badge variant="secondary">思维链</Badge>
                <Badge variant="secondary">引用溯源</Badge>
              </div>
              <Link href="/knowseeker">
                <Button className="w-full mt-2 gap-2">
                  开始使用 <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
            </CardContent>
          </Card>

          {/* TripMind Card */}
          <Card className="group relative overflow-hidden border-2 transition-all hover:border-primary/50 hover:shadow-lg">
            <CardHeader className="pb-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                  <Plane className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <CardTitle className="text-xl">TripMind</CardTitle>
                  <CardDescription>多 Agent 旅游规划</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-muted-foreground">
                多 Agent 协同编排 — 6 个专业 Agent 并行协作，
                实时生成包含天气、交通、住宿、行程和预算的完整旅行方案。
              </p>
              <div className="flex flex-wrap gap-2">
                <Badge variant="secondary">Multi-Agent</Badge>
                <Badge variant="secondary">MCP 协议</Badge>
                <Badge variant="secondary">SSE 流式</Badge>
                <Badge variant="secondary">追问调整</Badge>
              </div>
              <Link href="/tripmind">
                <Button className="w-full mt-2 gap-2">
                  开始规划 <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
            </CardContent>
          </Card>
        </div>

        {/* Footer info */}
        <p className="text-center text-xs text-muted-foreground">
          Powered by DeepSeek API + Ollama Embedding + ChromaDB + MCP Protocol
        </p>
      </div>
    </div>
  );
}
