"use client";

import { useState, useEffect } from "react";
import { Settings, Loader2, CheckCircle2, AlertCircle } from "lucide-react";
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

    // Load settings on mount
    useEffect(() => {
        const load = async () => {
            try {
                const res = await fetch(`${API_BASE}/api/settings`);
                if (res.ok) {
                    const data = await res.json();
                    if (data.backend) setBackend(data.backend);
                    if (data.model) setModel(data.model);
                    if (data.api_key) setApiKey(data.api_key);
                    if (data.base_url) setBaseUrl(data.base_url);
                }
            } catch {
                // Backend not available, use defaults
            }
        };
        load();
    }, []);

    // Fetch models when mount or backend changes
    useEffect(() => {
        const fetchModels = async () => {
            setModelsLoading(true);
            try {
                const res = await fetch(`${API_BASE}/api/models?backend=${encodeURIComponent(backend)}`);
                if (res.ok) {
                    const data = await res.json();
                    const list = Array.isArray(data.models) ? data.models : [];
                    setModels(list);
                    // Auto-select first if none selected
                    setModel((prev) => prev || list[0] || "");
                }
            } catch {
                const fallback =
                    backend === "ollama"
                        ? ["gemma4:latest"]
                        : [
                              "deepseek-chat",
                              "deepseek-reasoner",
                              "deepseek-coder",
                          ];
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
                    message: `✅ 配置已保存 — ${backend} / ${model}`,
                });
            } else {
                const err = await res
                    .json()
                    .catch(() => ({ detail: "保存失败" }));
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

    return (
        <div className="flex-1 overflow-auto p-4 md:p-8">
            <div className="max-w-2xl mx-auto space-y-6">
                {/* Header */}
                <div className="flex items-center gap-2">
                    <Settings className="h-6 w-6 text-primary" />
                    <h1 className="text-2xl font-bold">系统设置</h1>
                </div>
                <p className="text-muted-foreground">
                    配置 AI 模型后端和连接参数。
                </p>

                {/* Backend Settings */}
                <Card>
                    <CardHeader>
                        <CardTitle className="text-lg">后端配置</CardTitle>
                        <CardDescription>
                            选择 LLM 后端并配置连接参数
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                        {/* Backend Selector */}
                        <div className="space-y-2">
                            <Label>LLM 后端</Label>
                            <div className="flex gap-3">
                                <button
                                    onClick={() => setBackend("deepseek")}
                                    className={`flex-1 rounded-md border-2 px-4 py-3 text-sm font-medium transition-all ${
                                        backend === "deepseek"
                                            ? "border-primary bg-primary/5 text-primary"
                                            : "border-muted hover:border-muted-foreground/30"
                                    }`}
                                >
                                    <div className="text-base mb-1">
                                        🚀 DeepSeek
                                    </div>
                                    <div className="text-xs text-muted-foreground">
                                        API 云端调用
                                    </div>
                                </button>
                                <button
                                    onClick={() => setBackend("ollama")}
                                    className={`flex-1 rounded-md border-2 px-4 py-3 text-sm font-medium transition-all ${
                                        backend === "ollama"
                                            ? "border-primary bg-primary/5 text-primary"
                                            : "border-muted hover:border-muted-foreground/30"
                                    }`}
                                >
                                    <div className="text-base mb-1">
                                        🦙 Ollama
                                    </div>
                                    <div className="text-xs text-muted-foreground">
                                        本地部署
                                    </div>
                                </button>
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
                            <div className="space-y-2">
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
                                    className={`flex items-center gap-2 text-sm ${
                                        status.type === "success"
                                            ? "text-green-600 dark:text-green-400"
                                            : "text-destructive"
                                    }`}
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
                <Card>
                    <CardHeader>
                        <CardTitle className="text-lg">当前配置</CardTitle>
                    </CardHeader>
                    <CardContent>
                        <dl className="space-y-2 text-sm">
                            <div className="flex justify-between">
                                <dt className="text-muted-foreground">后端</dt>
                                <dd className="font-medium">{backend}</dd>
                            </div>
                            <div className="flex justify-between">
                                <dt className="text-muted-foreground">模型</dt>
                                <dd className="font-medium">
                                    {model || "未选择"}
                                </dd>
                            </div>
                            <div className="flex justify-between">
                                <dt className="text-muted-foreground">
                                    Base URL
                                </dt>
                                <dd className="font-medium truncate ml-4 max-w-[200px]">
                                    {baseUrl || "默认"}
                                </dd>
                            </div>
                            {backend === "deepseek" && (
                                <div className="flex justify-between">
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
