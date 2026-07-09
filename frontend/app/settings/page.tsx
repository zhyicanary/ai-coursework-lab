"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import {
    Settings,
    Loader2,
    CheckCircle2,
    AlertCircle,
    Rocket,
    Server,
    Wifi,
    WifiOff,
    Brain,
    Boxes,
    Filter,
    Cpu,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Card,
    CardHeader,
    CardTitle,
    CardDescription,
    CardContent,
} from "@/components/ui/card";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Switch } from "@/components/ui/switch";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { API_BASE } from "@/lib/config";

interface FullSettings {
    // 推理层
    backend: string;
    model: string;
    api_key: string;
    base_url: string;
    // 向量化层
    embedding_model: string;
    embedding_base_url: string;
    // 重排序层
    reranker_model: string;
    reranker_enabled: boolean;
}

export default function SettingsPage() {
    // ── 推理层 ──
    const [backend, setBackend] = useState<"deepseek" | "ollama">("deepseek");
    const [model, setModel] = useState("");
    const [models, setModels] = useState<string[]>([]);
    const [apiKey, setApiKey] = useState("");
    const [baseUrl, setBaseUrl] = useState("https://api.deepseek.com");

    // ── 向量化层 ──
    const [embModel, setEmbModel] = useState("qwen3-embedding:8b");
    const [embBaseUrl, setEmbBaseUrl] = useState("http://localhost:11434/v1");

    // ── 重排序层 ──
    const [rerankerModel, setRerankerModel] = useState("BAAI/bge-reranker-v2-m3");
    const [rerankerEnabled, setRerankerEnabled] = useState(true);

    // ── UI 状态 ──
    const [loading, setLoading] = useState(false);
    const [modelsLoading, setModelsLoading] = useState(false);
    const [backendOnline, setBackendOnline] = useState<boolean | null>(null);
    const [settingsLoaded, setSettingsLoaded] = useState(false);

    const loadSettings = useCallback(async () => {
        try {
            const res = await fetch(`${API_BASE}/api/settings`);
            if (res.ok) {
                setBackendOnline(true);
                const data = await res.json();
                setBackend(data.backend || "deepseek");
                const restoredModel = data.model || "";
                setModel(restoredModel);
                savedModelRef.current = restoredModel;
                setApiKey(data.api_key || "");
                setBaseUrl(data.base_url || "https://api.deepseek.com");
                setEmbModel(data.embedding_model || "qwen3-embedding:8b");
                setEmbBaseUrl(data.embedding_base_url || "http://localhost:11434/v1");
                setRerankerModel(data.reranker_model || "BAAI/bge-reranker-v2-m3");
                setRerankerEnabled(data.reranker_enabled !== false);
            }
        } catch {
            setBackendOnline(false);
        } finally {
            setSettingsLoaded(true);
        }
    }, []);

    useEffect(() => {
        loadSettings();
    }, [loadSettings]);

    useEffect(() => {
        if (backend === "ollama") {
            setBaseUrl((prev) =>
                prev.includes("deepseek") ? "http://localhost:11434/v1" : prev,
            );
        } else {
            setBaseUrl((prev) =>
                prev.includes("localhost") || prev.includes("11434")
                    ? "https://api.deepseek.com"
                    : prev,
            );
        }
    }, [backend]);

    // 追踪当前 backend，用于忽略已过期的异步响应
    const backendRef = useRef(backend);
    // 追踪 loadSettings 恢复的模型，避免被模型列表覆盖
    const savedModelRef = useRef<string | null>(null);
    useEffect(() => {
        backendRef.current = backend;
    }, [backend]);

    useEffect(() => {
        // 等待 loadSettings 完成再拉模型列表，避免用默认值 "deepseek"
        // 发起请求后又被真实配置（如 ollama）的响应覆盖
        if (!settingsLoaded) return;

        const currentBackend = backend;
        setModelsLoading(true);
        const fetchModels = async () => {
            try {
                const res = await fetch(
                    `${API_BASE}/api/models?backend=${encodeURIComponent(currentBackend)}`,
                );
                if (res.ok) {
                    const data = await res.json();
                    // 忽略过期的响应：组件已切换到另一个 backend
                    if (currentBackend !== backendRef.current) return;
                    const list = Array.isArray(data.models) ? data.models : [];
                    setModels(list);
                    // 保留已保存的模型（如果它在列表中），否则选第一个
                    const saved = savedModelRef.current;
                    if (saved && list.includes(saved)) {
                        setModel(saved);
                    } else if (list.length > 0) {
                        setModel(list[0]);
                    }
                    savedModelRef.current = null;
                }
            } catch {
                if (currentBackend !== backendRef.current) return;
                const fallback =
                    currentBackend === "ollama"
                        ? ["gemma3:latest"]
                        : ["deepseek-chat", "deepseek-reasoner"];
                setModels(fallback);
                if (fallback.length > 0) {
                    setModel(fallback[0]);
                }
            } finally {
                if (currentBackend === backendRef.current) {
                    setModelsLoading(false);
                }
            }
        };
        fetchModels();
    }, [backend, settingsLoaded]);

    const handleSave = async () => {
        setLoading(true);
        try {
            const res = await fetch(`${API_BASE}/api/settings`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    backend,
                    model,
                    api_key: apiKey,
                    base_url: baseUrl,
                    embedding_model: embModel,
                    embedding_base_url: embBaseUrl,
                    reranker_model: rerankerModel,
                    reranker_enabled: rerankerEnabled,
                }),
            });

            if (res.ok) {
                toast.success("配置已保存", {
                    description: `推理: ${model} · 向量化: ${embModel} · 重排序: ${rerankerEnabled ? "开启" : "关闭"}`,
                });
            } else {
                const err = await res.json().catch(() => ({ detail: "保存失败" }));
                throw new Error(err.detail || "保存失败");
            }
        } catch (err) {
            toast.error(err instanceof Error ? err.message : "保存设置失败");
        } finally {
            setLoading(false);
        }
    };

    const backendOptions = [
        {
            value: "deepseek" as const,
            icon: Rocket,
            label: "DeepSeek",
            desc: "API 云端调用",
            gradient: "from-violet-500 to-blue-500",
        },
        {
            value: "ollama" as const,
            icon: Server,
            label: "Ollama",
            desc: "本地部署",
            gradient: "from-emerald-500 to-teal-500",
        },
    ];

    return (
        <div className="scrollbar-thin overflow-auto p-4 md:p-8">
            <div className="mx-auto flex max-w-2xl flex-col gap-6">
                {/* Header */}
                <div className="flex items-center gap-3 animate-fade-in">
                    <div className="flex size-10 items-center justify-center rounded-xl bg-gradient-to-br from-amber-500/15 to-orange-500/15 ring-1 ring-amber-500/20">
                        <Settings className="size-5 text-amber-600 dark:text-amber-400" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold">系统设置</h1>
                        <p className="text-sm text-muted-foreground">
                            三层模型独立配置 — 推理、向量化、重排序
                        </p>
                    </div>
                    <div className="ml-auto">
                        {backendOnline === true && (
                            <Badge
                                variant="secondary"
                                className="gap-1 text-emerald-600 dark:text-emerald-400"
                            >
                                <Wifi className="size-3" />
                                已连接
                            </Badge>
                        )}
                        {backendOnline === false && (
                            <Badge variant="destructive" className="gap-1">
                                <WifiOff className="size-3" />
                                未连接
                            </Badge>
                        )}
                    </div>
                </div>

                {/* Offline Alert */}
                {backendOnline === false && (
                    <Alert variant="warning">
                        <AlertCircle className="size-4" />
                        <AlertDescription>
                            后端服务未运行。请在项目根目录执行{" "}
                            <code className="rounded bg-muted px-1.5 py-0.5 text-xs">
                                uv run uvicorn backend.server:app --port 8000
                            </code>{" "}
                            启动后端。
                        </AlertDescription>
                    </Alert>
                )}

                {/* ═══ 推理生成模型 ═══ */}
                <Card className="animate-fade-in-up overflow-hidden">
                    <CardHeader className="border-b bg-muted/30">
                        <div className="flex items-center gap-2">
                            <div className="flex size-8 items-center justify-center rounded-lg bg-violet-500/10 ring-1 ring-violet-500/20">
                                <Brain className="size-4 text-violet-600 dark:text-violet-400" />
                            </div>
                            <div>
                                <CardTitle className="text-base">
                                    推理生成模型
                                </CardTitle>
                                <CardDescription>
                                    分析问题、评估结果、生成回答
                                </CardDescription>
                            </div>
                        </div>
                    </CardHeader>
                    <CardContent className="flex flex-col gap-6 pt-4">
                        {/* Backend Selector */}
                        <div className="flex flex-col gap-2">
                            <Label>后端</Label>
                            <div className="grid gap-3 sm:grid-cols-2">
                                {backendOptions.map((opt) => {
                                    const Icon = opt.icon;
                                    const active = backend === opt.value;
                                    return (
                                        <button
                                            key={opt.value}
                                            onClick={() => setBackend(opt.value)}
                                            className={cn(
                                                "relative flex items-center gap-3 rounded-xl border-2 p-4 text-left transition-colors",
                                                active
                                                    ? "border-primary bg-primary/5"
                                                    : "border-border hover:border-muted-foreground/30 hover:bg-accent/50",
                                            )}
                                        >
                                            <div
                                                className={cn(
                                                    "flex size-10 items-center justify-center rounded-lg bg-gradient-to-br text-white shadow-sm",
                                                    opt.gradient,
                                                )}
                                            >
                                                <Icon className="size-5" />
                                            </div>
                                            <div>
                                                <p className="text-sm font-medium">
                                                    {opt.label}
                                                </p>
                                                <p className="text-xs text-muted-foreground">
                                                    {opt.desc}
                                                </p>
                                            </div>
                                            {active && (
                                                <div className="absolute right-3 top-3 flex size-5 items-center justify-center rounded-full bg-primary">
                                                    <CheckCircle2 className="size-3 text-primary-foreground" />
                                                </div>
                                            )}
                                        </button>
                                    );
                                })}
                            </div>
                        </div>

                        {/* Model */}
                        <div className="flex flex-col gap-2">
                            <Label htmlFor="llm-model">模型</Label>
                            <Select
                                value={model}
                                onValueChange={setModel}
                                disabled={modelsLoading}
                            >
                                <SelectTrigger id="llm-model">
                                    <SelectValue
                                        placeholder={
                                            modelsLoading
                                                ? "加载中…"
                                                : model
                                                  ? undefined
                                                  : "选择模型"
                                        }
                                    />
                                </SelectTrigger>
                                <SelectContent>
                                    {models.map((m) => (
                                        <SelectItem key={m} value={m}>
                                            {m}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>

                        {/* API Key */}
                        {backend === "deepseek" && (
                            <div className="flex flex-col gap-2 animate-fade-in">
                                <Label htmlFor="api-key">API Key</Label>
                                <Input
                                    id="api-key"
                                    type="password"
                                    placeholder="sk-…"
                                    value={apiKey}
                                    onChange={(e) => setApiKey(e.target.value)}
                                    autoComplete="off"
                                    spellCheck={false}
                                />
                                <p className="text-xs text-muted-foreground">
                                    DeepSeek API 密钥，不会明文显示
                                </p>
                            </div>
                        )}

                        {/* Base URL */}
                        <div className="flex flex-col gap-2">
                            <Label htmlFor="base-url">Base URL</Label>
                            <Input
                                id="base-url"
                                placeholder={
                                    backend === "deepseek"
                                        ? "https://api.deepseek.com"
                                        : "http://localhost:11434/v1"
                                }
                                value={baseUrl}
                                onChange={(e) => setBaseUrl(e.target.value)}
                                autoComplete="off"
                                spellCheck={false}
                            />
                        </div>
                    </CardContent>
                </Card>

                {/* ═══ 向量化模型 ═══ */}
                <Card className="animate-fade-in-up overflow-hidden">
                    <CardHeader className="border-b bg-muted/30">
                        <div className="flex items-center gap-2">
                            <div className="flex size-8 items-center justify-center rounded-lg bg-cyan-500/10 ring-1 ring-cyan-500/20">
                                <Boxes className="size-4 text-cyan-600 dark:text-cyan-400" />
                            </div>
                            <div>
                                <CardTitle className="text-base">
                                    向量化模型
                                </CardTitle>
                                <CardDescription>
                                    文档分块向量化、查询向量化
                                </CardDescription>
                            </div>
                            <Badge
                                variant="secondary"
                                className="ml-auto gap-1 text-xs"
                            >
                                <Cpu className="size-3" />
                                本地
                            </Badge>
                        </div>
                    </CardHeader>
                    <CardContent className="flex flex-col gap-6 pt-4">
                        <div className="flex flex-col gap-2">
                            <Label htmlFor="emb-model">模型名称</Label>
                            <Input
                                id="emb-model"
                                placeholder="qwen3-embedding:8b"
                                value={embModel}
                                onChange={(e) => setEmbModel(e.target.value)}
                                autoComplete="off"
                                spellCheck={false}
                            />
                            <p className="text-xs text-muted-foreground">
                                需已在 Ollama 中拉取该模型（ollama pull）
                            </p>
                        </div>

                        <div className="flex flex-col gap-2">
                            <Label htmlFor="emb-url">Ollama 服务地址</Label>
                            <Input
                                id="emb-url"
                                placeholder="http://localhost:11434/v1"
                                value={embBaseUrl}
                                onChange={(e) => setEmbBaseUrl(e.target.value)}
                                autoComplete="off"
                                spellCheck={false}
                            />
                            <p className="text-xs text-muted-foreground">
                                DeepSeek API 无 Embedding 接口，固定使用本地 Ollama
                            </p>
                        </div>
                    </CardContent>
                </Card>

                {/* ═══ 重排序模型 ═══ */}
                <Card className="animate-fade-in-up overflow-hidden">
                    <CardHeader className="border-b bg-muted/30">
                        <div className="flex items-center gap-2">
                            <div className="flex size-8 items-center justify-center rounded-lg bg-amber-500/10 ring-1 ring-amber-500/20">
                                <Filter className="size-4 text-amber-600 dark:text-amber-400" />
                            </div>
                            <div>
                                <CardTitle className="text-base">
                                    重排序模型
                                </CardTitle>
                                <CardDescription>
                                    Cross-Encoder 精排序，提升检索精度
                                </CardDescription>
                            </div>
                            <Badge
                                variant="secondary"
                                className="ml-auto gap-1 text-xs"
                            >
                                <Cpu className="size-3" />
                                本地
                            </Badge>
                        </div>
                    </CardHeader>
                    <CardContent className="flex flex-col gap-6 pt-4">
                        {/* Enable Switch */}
                        <div className="flex items-center justify-between rounded-lg border p-4">
                            <div className="flex flex-col gap-0.5">
                                <Label htmlFor="reranker-switch">
                                    启用重排序
                                </Label>
                                <p className="text-xs text-muted-foreground">
                                    关闭后降级为纯向量检索
                                </p>
                            </div>
                            <Switch
                                id="reranker-switch"
                                checked={rerankerEnabled}
                                onCheckedChange={setRerankerEnabled}
                            />
                        </div>

                        {/* Model Name */}
                        <div
                            className={cn(
                                "flex flex-col gap-2 transition-opacity",
                                !rerankerEnabled && "pointer-events-none opacity-40",
                            )}
                        >
                            <Label htmlFor="reranker-model">模型名称</Label>
                            <Input
                                id="reranker-model"
                                placeholder="BAAI/bge-reranker-v2-m3"
                                value={rerankerModel}
                                onChange={(e) =>
                                    setRerankerModel(e.target.value)
                                }
                                autoComplete="off"
                                spellCheck={false}
                            />
                            <p className="text-xs text-muted-foreground">
                                首次使用自动从 HuggingFace 下载（约 560MB）
                            </p>
                        </div>
                    </CardContent>
                </Card>

                {/* Save Button */}
                <div className="flex items-center justify-end gap-4">
                    <Button onClick={handleSave} disabled={loading} size="lg">
                        {loading ? (
                            <Loader2
                                className="size-4 animate-spin"
                                data-icon="inline-start"
                            />
                        ) : (
                            <CheckCircle2
                                className="size-4"
                                data-icon="inline-start"
                            />
                        )}
                        {loading ? "保存中…" : "保存设置"}
                    </Button>
                </div>

                {/* Current Config Summary */}
                <Card className="animate-fade-in-up">
                    <CardHeader className="border-b bg-muted/30">
                        <CardTitle className="text-base">当前配置</CardTitle>
                    </CardHeader>
                    <CardContent className="pt-4">
                        <div className="flex flex-col gap-4">
                            {/* 推理层 */}
                            <div className="flex flex-col gap-2">
                                <div className="flex items-center gap-1.5 text-xs font-medium text-violet-600 dark:text-violet-400">
                                    <Brain className="size-3" />
                                    推理生成
                                </div>
                                <dl className="grid gap-2 text-sm sm:grid-cols-2">
                                    <div className="flex items-center justify-between rounded-lg border p-2.5">
                                        <dt className="text-muted-foreground">
                                            后端
                                        </dt>
                                        <dd>
                                            <Badge variant="secondary">
                                                {backend}
                                            </Badge>
                                        </dd>
                                    </div>
                                    <div className="flex items-center justify-between rounded-lg border p-2.5">
                                        <dt className="text-muted-foreground">
                                            模型
                                        </dt>
                                        <dd className="max-w-[140px] truncate font-medium">
                                            {model || "未选择"}
                                        </dd>
                                    </div>
                                </dl>
                            </div>

                            <Separator />

                            {/* 向量化层 */}
                            <div className="flex flex-col gap-2">
                                <div className="flex items-center gap-1.5 text-xs font-medium text-cyan-600 dark:text-cyan-400">
                                    <Boxes className="size-3" />
                                    向量化
                                </div>
                                <dl className="grid gap-2 text-sm sm:grid-cols-2">
                                    <div className="flex items-center justify-between rounded-lg border p-2.5">
                                        <dt className="text-muted-foreground">
                                            模型
                                        </dt>
                                        <dd className="max-w-[140px] truncate font-medium">
                                            {embModel}
                                        </dd>
                                    </div>
                                    <div className="flex items-center justify-between rounded-lg border p-2.5">
                                        <dt className="text-muted-foreground">
                                            地址
                                        </dt>
                                        <dd className="max-w-[140px] truncate font-medium">
                                            {embBaseUrl}
                                        </dd>
                                    </div>
                                </dl>
                            </div>

                            <Separator />

                            {/* 重排序层 */}
                            <div className="flex flex-col gap-2">
                                <div className="flex items-center gap-1.5 text-xs font-medium text-amber-600 dark:text-amber-400">
                                    <Filter className="size-3" />
                                    重排序
                                </div>
                                <dl className="grid gap-2 text-sm sm:grid-cols-2">
                                    <div className="flex items-center justify-between rounded-lg border p-2.5">
                                        <dt className="text-muted-foreground">
                                            状态
                                        </dt>
                                        <dd>
                                            <Badge
                                                variant="secondary"
                                                className={cn(
                                                    rerankerEnabled
                                                        ? "text-emerald-600 dark:text-emerald-400"
                                                        : "text-muted-foreground",
                                                )}
                                            >
                                                {rerankerEnabled
                                                    ? "已启用"
                                                    : "已关闭"}
                                            </Badge>
                                        </dd>
                                    </div>
                                    <div className="flex items-center justify-between rounded-lg border p-2.5">
                                        <dt className="text-muted-foreground">
                                            模型
                                        </dt>
                                        <dd className="max-w-[140px] truncate font-medium">
                                            {rerankerModel}
                                        </dd>
                                    </div>
                                </dl>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
