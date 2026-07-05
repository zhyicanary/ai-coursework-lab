import Link from "next/link";
import {
    Search,
    Plane,
    ArrowRight,
    Brain,
    Sparkles,
    Layers,
    Zap,
    Bot,
    Network,
    Database,
    GitBranch,
    Cpu,
    FileSearch,
    Users,
    Workflow,
} from "lucide-react";
import {
    Card,
    CardHeader,
    CardTitle,
    CardDescription,
    CardContent,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

const techStack = [
    { label: "LangGraph", icon: Layers },
    { label: "MCP 协议", icon: Zap },
    { label: "DeepSeek", icon: Brain },
    { label: "ChromaDB", icon: Sparkles },
];

const stats = [
    { value: "7", label: "AI Agent", icon: Bot },
    { value: "2", label: "应用场景", icon: Network },
    { value: "5+", label: "MCP 工具", icon: Zap },
    { value: "100%", label: "开源", icon: Sparkles },
];

const features = [
    {
        icon: Bot,
        title: "自主决策",
        desc: "Agent 自主判断检索轮次和策略，无需人工干预",
        color: "text-violet-500",
    },
    {
        icon: Network,
        title: "多智能体协同",
        desc: "6 个专业 Agent 按 DAG 依赖并行协作",
        color: "text-cyan-500",
    },
    {
        icon: Zap,
        title: "MCP 标准化",
        desc: "工具调用协议标准化，支持熔断降级",
        color: "text-amber-500",
    },
    {
        icon: GitBranch,
        title: "LangGraph 编排",
        desc: "状态机驱动，支持条件分支和循环",
        color: "text-emerald-500",
    },
];

const architecture = [
    {
        layer: "前端展示层",
        tech: "Next.js + shadcn/ui",
        icon: Layers,
        items: ["统一前端框架", "实时 SSE 流式更新", "暗色模式"],
    },
    {
        layer: "Agent 编排层",
        tech: "LangGraph + LangChain",
        icon: Workflow,
        items: ["状态机编排", "DAG 依赖调度", "并行/顺序执行"],
    },
    {
        layer: "MCP 工具层",
        tech: "Python MCP SDK",
        icon: Zap,
        items: ["标准化工具协议", "双路径调用", "自动熔断降级"],
    },
    {
        layer: "AI 模型层",
        tech: "DeepSeek / Ollama",
        icon: Cpu,
        items: ["双后端热切换", "OpenAI 兼容接口", "本地 Embedding"],
    },
    {
        layer: "数据存储层",
        tech: "ChromaDB",
        icon: Database,
        items: ["向量检索", "景点知识库", "文档向量化"],
    },
];

export default function HomePage() {
    return (
        <div className="flex flex-col min-h-[calc(100vh-3.5rem)]">
            {/* Hero Section */}
            <section className="relative overflow-hidden border-b">
                <div className="absolute inset-0 bg-gradient-to-br from-violet-50 via-blue-50 to-cyan-50 dark:from-violet-950/30 dark:via-blue-950/20 dark:to-transparent" />
                <div
                    className="absolute inset-0 opacity-30 dark:opacity-20"
                    style={{
                        backgroundImage:
                            "radial-gradient(circle at 20% 50%, rgba(120, 119, 198, 0.15), transparent 50%), radial-gradient(circle at 80% 80%, rgba(255, 119, 198, 0.1), transparent 50%)",
                    }}
                />

                <div className="relative mx-auto max-w-4xl px-4 py-16 md:py-24 text-center">
                    <div className="mb-6 flex justify-center animate-fade-in">
                        <div className="flex size-16 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-500 to-blue-500 shadow-lg shadow-violet-500/25">
                            <Brain className="size-8 text-white" />
                        </div>
                    </div>

                    <h1 className="text-4xl font-bold tracking-tight md:text-5xl animate-fade-in-up">
                        AI Coursework{" "}
                        <span className="text-gradient">Lab</span>
                    </h1>

                    <p className="mx-auto mt-4 max-w-2xl text-base text-muted-foreground md:text-lg animate-fade-in-up">
                        基于统一技术底座（大模型 + LangGraph + MCP），
                        探索两种 AI Agent 应用范式 —
                        深度推理与协同编排。
                    </p>

                    <div className="mt-8 flex flex-wrap justify-center gap-2 animate-fade-in">
                        {techStack.map((tech) => {
                            const Icon = tech.icon;
                            return (
                                <Badge
                                    key={tech.label}
                                    variant="secondary"
                                    className="gap-1.5 px-3 py-1 text-sm"
                                >
                                    <Icon className="size-3.5" />
                                    {tech.label}
                                </Badge>
                            );
                        })}
                    </div>
                </div>
            </section>

            {/* Stats Section */}
            <section className="border-b bg-muted/30">
                <div className="mx-auto max-w-4xl px-4 py-8">
                    <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                        {stats.map((stat) => {
                            const Icon = stat.icon;
                            return (
                                <div
                                    key={stat.label}
                                    className="flex flex-col items-center gap-1 text-center"
                                >
                                    <Icon className="size-5 text-primary/60" />
                                    <span className="text-2xl font-bold text-gradient">
                                        {stat.value}
                                    </span>
                                    <span className="text-xs text-muted-foreground">
                                        {stat.label}
                                    </span>
                                </div>
                            );
                        })}
                    </div>
                </div>
            </section>

            {/* Project Cards */}
            <section className="mx-auto w-full max-w-4xl px-4 py-12 md:py-16">
                <div className="grid gap-6 md:grid-cols-2">
                    {/* KnowSeeker Card */}
                    <Link
                        href="/knowseeker"
                        className="group animate-fade-in-up"
                        style={{ animationDelay: "0.1s" }}
                    >
                        <Card className="gradient-border glow-on-hover h-full overflow-hidden border-2 transition-all hover:-translate-y-1">
                            <CardHeader className="pb-4">
                                <div className="flex items-center gap-3">
                                    <div className="flex size-11 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500/15 to-blue-500/15 ring-1 ring-violet-500/20">
                                        <Search className="size-5 text-violet-600 dark:text-violet-400" />
                                    </div>
                                    <div>
                                        <CardTitle className="text-xl">
                                            KnowSeeker
                                        </CardTitle>
                                        <CardDescription>
                                            Agentic RAG 知识助手
                                        </CardDescription>
                                    </div>
                                </div>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <p className="text-sm text-muted-foreground leading-relaxed">
                                    单 Agent 深度推理 — 上传文档构建知识库，
                                    AI 自主分析问题并制定多轮检索策略，
                                    生成带引用的精准回答。
                                </p>
                                <div className="flex flex-wrap gap-1.5">
                                    <Badge variant="outline" className="text-xs">
                                        Agentic RAG
                                    </Badge>
                                    <Badge variant="outline" className="text-xs">
                                        向量检索
                                    </Badge>
                                    <Badge variant="outline" className="text-xs">
                                        思维链
                                    </Badge>
                                    <Badge variant="outline" className="text-xs">
                                        引用溯源
                                    </Badge>
                                </div>
                                <div className="flex items-center gap-1.5 text-sm font-medium text-violet-600 dark:text-violet-400">
                                    开始使用
                                    <ArrowRight className="size-4 transition-transform group-hover:translate-x-1" />
                                </div>
                            </CardContent>
                        </Card>
                    </Link>

                    {/* TripMind Card */}
                    <Link
                        href="/tripmind"
                        className="group animate-fade-in-up"
                        style={{ animationDelay: "0.2s" }}
                    >
                        <Card className="gradient-border glow-on-hover h-full overflow-hidden border-2 transition-all hover:-translate-y-1">
                            <CardHeader className="pb-4">
                                <div className="flex items-center gap-3">
                                    <div className="flex size-11 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-500/15 to-teal-500/15 ring-1 ring-cyan-500/20">
                                        <Plane className="size-5 text-cyan-600 dark:text-cyan-400" />
                                    </div>
                                    <div>
                                        <CardTitle className="text-xl">
                                            TripMind
                                        </CardTitle>
                                        <CardDescription>
                                            多 Agent 旅游规划
                                        </CardDescription>
                                    </div>
                                </div>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <p className="text-sm text-muted-foreground leading-relaxed">
                                    多 Agent 协同编排 — 6 个专业 Agent
                                    并行协作，实时生成包含天气、交通、
                                    住宿、行程和预算的完整旅行方案。
                                </p>
                                <div className="flex flex-wrap gap-1.5">
                                    <Badge variant="outline" className="text-xs">
                                        Multi-Agent
                                    </Badge>
                                    <Badge variant="outline" className="text-xs">
                                        MCP 协议
                                    </Badge>
                                    <Badge variant="outline" className="text-xs">
                                        SSE 流式
                                    </Badge>
                                    <Badge variant="outline" className="text-xs">
                                        追问调整
                                    </Badge>
                                </div>
                                <div className="flex items-center gap-1.5 text-sm font-medium text-cyan-600 dark:text-cyan-400">
                                    开始规划
                                    <ArrowRight className="size-4 transition-transform group-hover:translate-x-1" />
                                </div>
                            </CardContent>
                        </Card>
                    </Link>
                </div>
            </section>

            {/* Feature Highlights */}
            <section className="mx-auto w-full max-w-4xl px-4 pb-12">
                <h2 className="mb-6 text-center text-2xl font-bold">
                    核心特性
                </h2>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                    {features.map((feat) => {
                        const Icon = feat.icon;
                        return (
                            <Card
                                key={feat.title}
                                className="transition-all hover:-translate-y-0.5 hover:shadow-md"
                            >
                            <CardContent className="pt-6">
                                <div className="flex flex-col items-start gap-3">
                                    <div className="flex size-10 items-center justify-center rounded-lg bg-muted">
                                        <Icon className={`size-5 ${feat.color}`} />
                                    </div>
                                    <div>
                                        <p className="font-medium">
                                            {feat.title}
                                        </p>
                                        <p className="text-sm text-muted-foreground mt-1">
                                            {feat.desc}
                                        </p>
                                    </div>
                                </div>
                            </CardContent>
                            </Card>
                        );
                    })}
                </div>
            </section>

            {/* Architecture Section */}
            <section className="border-t bg-muted/20">
                <div className="mx-auto max-w-4xl px-4 py-12 md:py-16">
                    <h2 className="mb-2 text-center text-2xl font-bold">
                        技术架构
                    </h2>
                    <p className="mb-8 text-center text-sm text-muted-foreground">
                        五层架构，统一技术底座，两个项目共享
                    </p>
                    <div className="flex flex-col gap-3">
                        {architecture.map((layer, idx) => {
                            const Icon = layer.icon;
                            return (
                                <div key={layer.layer}>
                                    <Card className="overflow-hidden transition-all hover:shadow-md">
                                        <CardContent className="flex items-center gap-4 p-4">
                                            <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/5 ring-1 ring-primary/10">
                                                <Icon className="size-5 text-primary/70" />
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-2 flex-wrap">
                                                    <span className="font-medium">
                                                        {layer.layer}
                                                    </span>
                                                    <Badge variant="secondary" className="text-xs">
                                                        {layer.tech}
                                                    </Badge>
                                                </div>
                                                <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1">
                                                    {layer.items.map((item) => (
                                                        <span
                                                            key={item}
                                                            className="text-xs text-muted-foreground"
                                                        >
                                                            {item}
                                                        </span>
                                                    ))}
                                                </div>
                                            </div>
                                            <span className="text-xs text-muted-foreground/50 font-mono shrink-0">
                                                L{architecture.length - idx}
                                            </span>
                                        </CardContent>
                                    </Card>
                                    {idx < architecture.length - 1 && (
                                        <div className="flex justify-center py-0.5">
                                            <div className="h-3 w-px bg-border" />
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </div>
            </section>

            {/* Footer */}
            <footer className="mt-auto border-t">
                <div className="mx-auto max-w-4xl px-4 py-6 text-center">
                    <p className="text-xs text-muted-foreground">
                        Powered by DeepSeek API + Ollama Embedding + ChromaDB +
                        MCP Protocol
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                        智能应用系统设计 — 课程设计作品集 © 2026
                    </p>
                </div>
            </footer>
        </div>
    );
}
