"use client";

import { useState, useEffect } from "react";
import {
    Settings,
    Loader2,
    CheckCircle2,
    AlertCircle,
    Rocket,
    Server,
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
import { cn } from "@/lib/utils";

const API_BASE = "http://localhost:8000";

export default function SettingsPage() {
    const [backend, setBackend] = useState<"deepseek" | "ollama">("deepseek");
    const [model, setModel] = useState("");
    const [models, setModels] = useState<string[]>([]);
    const [apiKey, setApiKey] = useState("");
    const [baseUrl, setBaseUrl] = useState("https://api.deepseek.com");
    const [loading, setLoading] = useState(false);
    const [modelsLoading, setModelsLoading] = useState(false);
    const [status, setStatus] = useState<{
        type: "success" | "error" | "";
        message: string;
    }>({ type: "", message: "" });

    useEffect(() => {
        const load = async () => {
            try {
                const res = await fetch(`${API_BASE}/api/settings`);
                if (res.ok) {
                    const data = await res.json();
                    const bk = data.backend || "deepseek";
                    setBackend(bk);
                    setModel(data.model || "");
                    setApiKey(data.api_key || "");
                    setBaseUrl(data.base_url || (bk === "ollama" ? "http://localhost:11434/v1" : "https://api.deepseek.com"));
                }
            } catch {
                // Backend not available, use defaults
            }
        };
        load();
    }, []);

    useEffect(() => {
        if (backend === "ollama") {
            setBaseUrl((prev) =>
                prev.includes("deepseek") ? "http://localhost:11434/v1" : prev
            );
            setModel((prev) =>
                prev.includes("deepseek") ? "" : prev
            );
        } else {
            setBaseUrl((prev) =>
                prev.includes("localhost") || prev.includes("11434")
                    ? "https://api.deepseek.com"
                    : prev
            );
            setModel((prev) =>
                prev && !prev.includes("deepseek") && !prev.includes("gpt") && !prev.includes("claude")
                    ? "" : prev
            );
        }
    }, [backend]);

    useEffect(() => {
        const fetchModels = async () => {
            setModelsLoading(true);
            try {
                const res = await fetch(`${API_BASE}/api/models?backend=${encodeURIComponent(backend)}`);
                if (res.ok) {
                    const data = await res.json();
                    const list = Array.isArray(data.models) ? data.models : [];
                    setModels(list);
                    setModel((prev) => prev || list[0] || "");
                }
            } catch {
                const fallback =
                    backend === "ollama"
                        ? ["gemma4:latest"]
                        : ["deepseek-chat", "deepseek-reasoner", "deepseek-coder"];
                setModels(fallback);
                setModel((prev) => prev || fallback[0]);
            } finally {
                setModelsLoading(false);
            }
        };
        fetchModels();
    }, [backend]);

    const handleSave = async () => {
        setLoading(true);
        setStatus({ type: "", message: "" });

        try {
            const res = await fetch(`${API_BASE}/api/settings`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    backend,
                    model,
                    api_key: apiKey,
                    base_url: baseUrl,
                }),
            });

            if (res.ok) {
                setStatus({
                    type: "success",
                    message: `配置已保存 — ${backend} / ${model}`,
                });
            } else {
                const err = await res.json().catch(() => ({ detail: "保存失败" }));
                throw new Error(err.detail || "保存失败");
            }
        } catch (err) {
            setStatus({
                type: "error",
                message: err instanceof Error ? err.message : "保存设置失败",
            });
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
            <div className="max-w-2xl mx-auto space-y-6">
                {/* Header */}
                <div className="flex items-center gap-3 animate-fade-in">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-amber-500/15 to-orange-500/15 ring-1 ring-amber-500/20">
                        <Settings className="h-5 w-5 text-amber-600 dark:text-amber-400" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold">系统设置</h1>
                        <p className="text-sm text-muted-foreground">
                            配置 AI 模型后端和连接参数
                        </p>
                    </div>
                </div>

                {/* Backend Settings */}
                <Card className="animate-fade-in-up overflow-hidden">
                    <CardHeader className="bg-muted/30 border-b">
                        <CardTitle className="text-base">后端配置</CardTitle>
                        <CardDescription>
                            选择 LLM 后端并配置连接参数
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6 pt-4">
                        {/* Backend Selector — Radio Cards */}
                        <div className="space-y-2">
                            <Label>LLM 后端</Label>
                            <div className="grid gap-3 sm:grid-cols-2">
                                {backendOptions.map((opt) => {
                                    const Icon = opt.icon;
                                    const active = backend === opt.value;
                                    return (
                                        <button
                                            key={opt.value}
                                            onClick={() => setBackend(opt.value)}
                                            className={cn(
                                                "relative flex items-center gap-3 rounded-xl border-2 p-4 text-left transition-all",
                                                active
                                                    ? "border-primary bg-primary/5"
                                                    : "border-border hover:border-muted-foreground/30 hover:bg-accent/50",
                                            )}
                                        >
                                            <div
                                                className={cn(
                                                    "flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br text-white shadow-sm",
                                                    opt.gradient,
                                                )}
                                            >
                                                <Icon className="h-5 w-5" />
                                            </div>
                                            <div>
                                                <p className="font-medium text-sm">
                                                    {opt.label}
                                                </p>
                                                <p className="text-xs text-muted-foreground">
                                                    {opt.desc}
                                                </p>
                                            </div>
                                            {active && (
                                                <div className="absolute right-3 top-3 flex h-5 w-5 items-center justify-center rounded-full bg-primary">
                                                    <CheckCircle2 className="h-3 w-3 text-primary-foreground" />
                                                </div>
                                            )}
                                        </button>
                                    );
                                })}
                            </div>
                        </div>

                        {/* Model */}
                        <div className="space-y-2">
                            <Label>模型</Label>
                            <Select
                                value={model}
                                onValueChange={setModel}
                                disabled={modelsLoading}
                            >
                                <SelectTrigger>
                                    <SelectValue
                                        placeholder={
                                            modelsLoading
                                                ? "加载中..."
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
                                    {models.length === 0 && !modelsLoading && (
                                        <SelectItem value="" disabled>
                                            暂无可用模型
                                        </SelectItem>
                                    )}
                                </SelectContent>
                            </Select>
                            <p className="text-xs text-muted-foreground">
                                从后端获取可用模型列表
                            </p>
                        </div>

                        {/* API Key - shown only for deepseek */}
                        {backend === "deepseek" && (
                            <div className="space-y-2 animate-fade-in">
                                <Label htmlFor="api-key">API Key</Label>
                                <Input
                                    id="api-key"
                                    type="password"
                                    placeholder="sk-..."
                                    value={apiKey}
                                    onChange={(e) => setApiKey(e.target.value)}
                                />
                                <p className="text-xs text-muted-foreground">
                                    DeepSeek API 密钥，不会明文显示
                                </p>
                            </div>
                        )}

                        {/* Base URL */}
                        <div className="space-y-2">
                            <Label htmlFor="base-url">Base URL</Label>
                            <Input
                                id="base-url"
                                placeholder={
                                    backend === "deepseek"
                                        ? "https://api.deepseek.com"
                                        : "http://localhost:11434"
                                }
                                value={baseUrl}
                                onChange={(e) => setBaseUrl(e.target.value)}
                            />
                            <p className="text-xs text-muted-foreground">
                                {backend === "deepseek"
                                    ? "DeepSeek API 地址"
                                    : "Ollama 本地服务地址"}
                            </p>
                        </div>

                        <Separator />

                        {/* Save Button */}
                        <div className="flex items-center gap-4">
                            <Button
                                onClick={handleSave}
                                disabled={loading}
                                className="gap-2"
                            >
                                {loading ? (
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                ) : (
                                    <CheckCircle2 className="h-4 w-4" />
                                )}
                                {loading ? "保存中..." : "保存设置"}
                            </Button>

                            {status.type && (
                                <div
                                    className={cn(
                                        "flex items-center gap-2 text-sm animate-fade-in",
                                        status.type === "success"
                                            ? "text-emerald-600 dark:text-emerald-400"
                                            : "text-destructive",
                                    )}
                                >
                                    {status.type === "success" ? (
                                        <CheckCircle2 className="h-4 w-4" />
                                    ) : (
                                        <AlertCircle className="h-4 w-4" />
                                    )}
                                    {status.message}
                                </div>
                            )}
                        </div>
                    </CardContent>
                </Card>

                {/* Current Config Info */}
                <Card className="animate-fade-in-up">
                    <CardHeader className="bg-muted/30 border-b">
                        <CardTitle className="text-base">当前配置</CardTitle>
                    </CardHeader>
                    <CardContent className="pt-4">
                        <dl className="grid gap-3 text-sm sm:grid-cols-2">
                            <div className="flex items-center justify-between rounded-lg border p-3">
                                <dt className="text-muted-foreground">后端</dt>
                                <dd>
                                    <Badge variant="secondary">
                                        {backend}
                                    </Badge>
                                </dd>
                            </div>
                            <div className="flex items-center justify-between rounded-lg border p-3">
                                <dt className="text-muted-foreground">模型</dt>
                                <dd className="font-medium truncate max-w-[140px]">
                                    {model || "未选择"}
                                </dd>
                            </div>
                            <div className="flex items-center justify-between rounded-lg border p-3 sm:col-span-2">
                                <dt className="text-muted-foreground">Base URL</dt>
                                <dd className="font-medium truncate max-w-[200px]">
                                    {baseUrl || "默认"}
                                </dd>
                            </div>
                            {backend === "deepseek" && (
                                <div className="flex items-center justify-between rounded-lg border p-3 sm:col-span-2">
                                    <dt className="text-muted-foreground">
                                        API Key
                                    </dt>
                                    <dd className="font-medium">
                                        {apiKey ? "••••••••" : "未设置"}
                                    </dd>
                                </div>
                            )}
                        </dl>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
