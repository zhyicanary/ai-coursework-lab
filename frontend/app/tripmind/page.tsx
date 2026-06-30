"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
    Plane,
    Send,
    Loader2,
    MapPin,
    Building2,
    Calendar,
    Banknote,
    Heart,
    TreePine,
    ShoppingBag,
    Umbrella,
    RefreshCw,
    Download,
    FileText,
    CheckCircle2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";

const API_BASE = "http://localhost:8000";
const STORAGE_KEY = "tripmind_plan";
const ADJUST_KEY = "tripmind_adjust";

interface AgentStatus {
    name: string;
    label: string;
    status: "pending" | "running" | "done" | "error";
    icon: React.ElementType;
}

const agentDefs: Omit<AgentStatus, "status">[] = [
    { name: "weather", label: "天气查询", icon: CloudIcon },
    { name: "transport", label: "交通查询", icon: TrainIcon },
    { name: "hotel", label: "酒店查询", icon: Building2 },
    { name: "itinerary", label: "行程规划", icon: Calendar },
    { name: "budget", label: "预算分析", icon: Banknote },
];

const preferencesList = [
    { key: "culture", label: "文化", icon: Heart },
    { key: "food", label: "美食", icon: CoffeeIcon },
    { key: "nature", label: "自然", icon: TreePine },
    { key: "shopping", label: "购物", icon: ShoppingBag },
    { key: "leisure", label: "休闲", icon: Umbrella },
];

function CloudIcon() {
    return (
        <svg
            className="h-4 w-4"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
        >
            <path d="M17.5 19H9a7 7 0 1 1 6.7-10 3.5 3.5 0 1 1 1.8 10Z" />
        </svg>
    );
}
function TrainIcon() {
    return (
        <svg
            className="h-4 w-4"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
        >
            <rect x="4" y="3" width="16" height="16" rx="2" />
            <path d="M4 11h16" />
            <path d="M12 3v8" />
            <circle cx="8" cy="16" r="2" />
            <circle cx="16" cy="16" r="2" />
        </svg>
    );
}
function CoffeeIcon() {
    return (
        <svg
            className="h-4 w-4"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
        >
            <path d="M17 8h1a4 4 0 1 1 0 8h-1" />
            <path d="M3 8h14v9a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4Z" />
            <line x1="6" y1="2" x2="6" y2="4" />
            <line x1="10" y1="2" x2="10" y2="4" />
            <line x1="14" y1="2" x2="14" y2="4" />
        </svg>
    );
}

export default function TripMindPage() {
    const [destination, setDestination] = useState("");
    const [departure, setDeparture] = useState("");
    const [days, setDays] = useState(3);
    const [budget, setBudget] = useState(5000);
    const [preferences, setPreferences] = useState<string[]>([
        "culture",
        "food",
    ]);
    const [planResult, setPlanResult] = useState<string | null>(null);
    const [agentStatuses, setAgentStatuses] = useState<AgentStatus[]>(
        agentDefs.map((a) => ({ ...a, status: "pending" })),
    );
    const [planning, setPlanning] = useState(false);
    const [adjustInput, setAdjustInput] = useState("");
    const [adjustLoading, setAdjustLoading] = useState(false);
    const [adjustResult, setAdjustResult] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [downloading, setDownloading] = useState(false);
    const [copied, setCopied] = useState(false);
    const [lastState, setLastState] = useState<Record<string, unknown> | null>(
        null,
    );
    const resultRef = useRef<HTMLDivElement>(null);

    // Restore results from localStorage on mount
    useEffect(() => {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved) {
            try {
                const parsed = JSON.parse(saved);
                setPlanResult(parsed.planResult);
                setAdjustResult(parsed.adjustResult || null);
                if (parsed.lastState) setLastState(parsed.lastState);
            } catch {
                // ignore corrupt data
            }
        }
    }, []);

    // Save planResult + adjustResult to localStorage whenever they change
    useEffect(() => {
        if (planResult) {
            localStorage.setItem(
                STORAGE_KEY,
                JSON.stringify({ planResult, adjustResult, lastState }),
            );
        }
    }, [planResult, adjustResult, lastState]);

    const togglePreference = (key: string) => {
        setPreferences((prev) =>
            prev.includes(key) ? prev.filter((p) => p !== key) : [...prev, key],
        );
    };

    const handlePlan = async () => {
        if (!destination.trim() || !departure.trim()) {
            setError("请填写目的地和出发城市");
            return;
        }

        setPlanning(true);
        setError(null);
        setPlanResult(null);
        setAdjustResult(null);
        setLastState(null);
        localStorage.removeItem(STORAGE_KEY);
        setAgentStatuses(agentDefs.map((a) => ({ ...a, status: "pending" })));

        try {
            const response = await fetch(`${API_BASE}/api/travel/plan/stream`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    destination: destination.trim(),
                    departure_city: departure.trim(),
                    days: days,
                    budget: budget,
                    preferences: preferences,
                }),
            });

            if (!response.ok) {
                throw new Error(`请求失败: ${response.statusText}`);
            }

            const reader = response.body?.getReader();
            if (!reader) throw new Error("无法读取响应流");

            const decoder = new TextDecoder();
            let buffer = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n");
                buffer = lines.pop() || "";

                for (const line of lines) {
                    if (line.startsWith("data: ")) {
                        const jsonStr = line.slice(6);
                        try {
                            const parsed = JSON.parse(jsonStr);

                            if (parsed.error) {
                                setError(parsed.error);
                            } else if (parsed.final_plan) {
                                setPlanResult(parsed.final_plan);
                            } else if (parsed.__full_state__) {
                                setLastState(parsed.__full_state__);
                            } else {
                                // Update agent statuses from state keys
                                const agentKeys: Record<string, string> = {
                                    weather_result: "weather",
                                    transport_result: "transport",
                                    hotel_result: "hotel",
                                    itinerary_result: "itinerary",
                                    budget_result: "budget",
                                };
                                for (const [key, agentName] of Object.entries(
                                    agentKeys,
                                )) {
                                    if (key in parsed) {
                                        const result = parsed[key];
                                        const status: AgentStatus["status"] =
                                            result
                                                ? result.error
                                                    ? "error"
                                                    : "done"
                                                : "running";
                                        setAgentStatuses((prev) =>
                                            prev.map((a) =>
                                                a.name === agentName
                                                    ? { ...a, status }
                                                    : a,
                                            ),
                                        );
                                    }
                                }
                            }
                        } catch {
                            // Skip unparseable lines
                        }
                    }
                }
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : "规划请求失败");
        } finally {
            setPlanning(false);
        }
    };

    const handleAdjust = async () => {
        const text = adjustInput.trim();
        if (!text || adjustLoading) return;
        if (!lastState) {
            setError("请先生成旅行方案后再进行调整");
            return;
        }

        setAdjustInput("");
        setAdjustLoading(true);
        setError(null);

        try {
            const res = await fetch(`${API_BASE}/api/travel/adjust`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ state: lastState, message: text }),
            });

            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                throw new Error(errData.detail || "调整请求失败");
            }

            const data = await res.json();
            const newPlan = data.final_plan as string | undefined;
            if (newPlan) {
                setPlanResult(newPlan);
                setLastState(data);
            }
            const adjustMsg = newPlan ? "方案已更新" : "调整完成";
            setAdjustResult(adjustMsg);
        } catch (err) {
            setError(err instanceof Error ? err.message : "调整请求失败");
        } finally {
            setAdjustLoading(false);
        }
    };

    // ── 下载 / 导出 ────────────────────────────────

    const buildFullReport = useCallback(() => {
        const date = new Date().toLocaleString("zh-CN");
        const lines = [
            `# 🗺️ 旅行方案 — ${destination || "未指定目的地"}`,
            ``,
            `**生成时间**: ${date}`,
            `**出发城市**: ${departure || "未指定"}`,
            `**天数**: ${days}`,
            `**预算**: ¥${budget.toLocaleString()}`,
            `**偏好**: ${preferences.map((p) => preferencesList.find((pl) => pl.key === p)?.label || p).join("、") || "无"}`,
            ``,
            `---`,
            ``,
            planResult || "（无方案数据）",
        ];
        if (adjustResult) {
            lines.push(``, `---`, `## 🔄 调整记录`, ``, adjustResult);
        }
        return lines.join("\n");
    }, [
        planResult,
        adjustResult,
        destination,
        departure,
        days,
        budget,
        preferences,
    ]);

    const handleDownloadMarkdown = () => {
        const content = buildFullReport();
        const blob = new Blob([content], {
            type: "text/markdown;charset=utf-8",
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `tripmind-${destination || "plan"}-${Date.now()}.md`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    const handleDownloadText = () => {
        const content = buildFullReport();
        const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `tripmind-${destination || "plan"}-${Date.now()}.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    };

    const handleCopyMarkdown = async () => {
        try {
            await navigator.clipboard.writeText(buildFullReport());
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        } catch {
            // fallback
        }
    };

    useEffect(() => {
        if (planResult && resultRef.current) {
            resultRef.current.scrollIntoView({ behavior: "smooth" });
        }
    }, [planResult]);

    const statusColor = (status: string) => {
        switch (status) {
            case "running":
                return "text-blue-500";
            case "done":
                return "text-green-500";
            case "error":
                return "text-red-500";
            default:
                return "text-muted-foreground";
        }
    };

    const statusDot = (status: string) => {
        const base = "inline-block h-2 w-2 rounded-full";
        switch (status) {
            case "running":
                return (
                    <span className={cn(base, "bg-blue-500 animate-pulse")} />
                );
            case "done":
                return <span className={cn(base, "bg-green-500")} />;
            case "error":
                return <span className={cn(base, "bg-red-500")} />;
            default:
                return <span className={cn(base, "bg-muted-foreground/30")} />;
        }
    };

    return (
        <div className="flex h-full">
            <div className="flex-1 overflow-auto p-4 md:p-8">
                <div className="max-w-4xl mx-auto space-y-6">
                    {/* Header */}
                    <div className="flex items-center gap-2">
                        <Plane className="h-6 w-6 text-primary" />
                        <h1 className="text-2xl font-bold">
                            TripMind 旅游规划
                        </h1>
                        <Badge variant="secondary" className="ml-2">
                            Multi-Agent
                        </Badge>
                    </div>
                    <p className="text-muted-foreground">
                        填写旅行需求，6 个专业 Agent
                        并行协作，为您生成完整的旅行方案。
                    </p>

                    {/* Form */}
                    <Card>
                        <CardHeader>
                            <CardTitle className="text-lg">旅行需求</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="grid gap-4 md:grid-cols-2">
                                <div className="space-y-2">
                                    <Label htmlFor="destination">目的地</Label>
                                    <div className="relative">
                                        <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                        <Input
                                            id="destination"
                                            className="pl-9"
                                            placeholder="e.g., 北京"
                                            value={destination}
                                            onChange={(e) =>
                                                setDestination(e.target.value)
                                            }
                                        />
                                    </div>
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="departure">出发城市</Label>
                                    <div className="relative">
                                        <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                        <Input
                                            id="departure"
                                            className="pl-9"
                                            placeholder="e.g., 上海"
                                            value={departure}
                                            onChange={(e) =>
                                                setDeparture(e.target.value)
                                            }
                                        />
                                    </div>
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="days">天数</Label>
                                    <Input
                                        id="days"
                                        type="number"
                                        min={1}
                                        max={30}
                                        value={days}
                                        onChange={(e) =>
                                            setDays(Number(e.target.value))
                                        }
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="budget">预算 (CNY)</Label>
                                    <Input
                                        id="budget"
                                        type="number"
                                        min={500}
                                        step={100}
                                        value={budget}
                                        onChange={(e) =>
                                            setBudget(Number(e.target.value))
                                        }
                                    />
                                </div>
                            </div>

                            <div className="space-y-2">
                                <Label>偏好</Label>
                                <div className="flex flex-wrap gap-2">
                                    {preferencesList.map((pref) => {
                                        const Icon = pref.icon;
                                        const active = preferences.includes(
                                            pref.key,
                                        );
                                        return (
                                            <button
                                                key={pref.key}
                                                onClick={() =>
                                                    togglePreference(pref.key)
                                                }
                                                className={cn(
                                                    "inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm font-medium transition-colors",
                                                    active
                                                        ? "bg-primary text-primary-foreground border-primary"
                                                        : "bg-background hover:bg-accent hover:text-accent-foreground",
                                                )}
                                            >
                                                <Icon className="h-3.5 w-3.5" />
                                                {pref.label}
                                            </button>
                                        );
                                    })}
                                </div>
                            </div>

                            <Button
                                className="w-full gap-2"
                                size="lg"
                                onClick={handlePlan}
                                disabled={planning}
                            >
                                {planning ? (
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                ) : (
                                    <Plane className="h-4 w-4" />
                                )}
                                {planning ? "规划中..." : "开始规划"}
                            </Button>
                        </CardContent>
                    </Card>

                    {/* Error */}
                    {error && (
                        <div className="rounded-md bg-destructive/10 px-4 py-3 text-sm text-destructive">
                            {error}
                            <button
                                className="ml-2 underline"
                                onClick={() => setError(null)}
                            >
                                关闭
                            </button>
                        </div>
                    )}

                    {/* Agent Status Panel */}
                    {planning && (
                        <Card>
                            <CardHeader>
                                <CardTitle className="text-lg">
                                    Agent 执行状态
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="grid gap-3 md:grid-cols-3">
                                    {agentStatuses.map((agent) => {
                                        const Icon = agent.icon;
                                        return (
                                            <div
                                                key={agent.name}
                                                className={cn(
                                                    "flex items-center gap-3 rounded-md border p-3 transition-colors",
                                                    agent.status ===
                                                        "running" &&
                                                        "border-blue-500/50 bg-blue-500/5",
                                                    agent.status === "done" &&
                                                        "border-green-500/50 bg-green-500/5",
                                                    agent.status === "error" &&
                                                        "border-red-500/50 bg-red-500/5",
                                                )}
                                            >
                                                <Icon />
                                                <div className="flex-1 min-w-0">
                                                    <p className="text-sm font-medium truncate">
                                                        {agent.label}
                                                    </p>
                                                    <div
                                                        className={cn(
                                                            "flex items-center gap-1.5 text-xs",
                                                            statusColor(
                                                                agent.status,
                                                            ),
                                                        )}
                                                    >
                                                        {statusDot(
                                                            agent.status,
                                                        )}
                                                        {agent.status ===
                                                            "pending" &&
                                                            "等待中"}
                                                        {agent.status ===
                                                            "running" &&
                                                            "执行中"}
                                                        {agent.status ===
                                                            "done" && "完成"}
                                                        {agent.status ===
                                                            "error" && "失败"}
                                                    </div>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            </CardContent>
                        </Card>
                    )}

                    {/* Plan Result + Download */}
                    {planResult && (
                        <Card ref={resultRef}>
                            <CardHeader>
                                <div className="flex items-center justify-between">
                                    <CardTitle className="text-lg">
                                        📋 旅行方案
                                    </CardTitle>
                                    <div className="flex gap-2">
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            className="gap-1.5"
                                            onClick={handleDownloadMarkdown}
                                        >
                                            <Download className="h-3.5 w-3.5" />
                                            MD
                                        </Button>
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            className="gap-1.5"
                                            onClick={handleDownloadText}
                                        >
                                            <FileText className="h-3.5 w-3.5" />
                                            TXT
                                        </Button>
                                        <Button
                                            variant="outline"
                                            size="sm"
                                            className="gap-1.5"
                                            onClick={handleCopyMarkdown}
                                        >
                                            {copied ? (
                                                <>
                                                    <CheckCircle2 className="h-3.5 w-3.5" />{" "}
                                                    已复制
                                                </>
                                            ) : (
                                                <>
                                                    <FileText className="h-3.5 w-3.5" />{" "}
                                                    复制
                                                </>
                                            )}
                                        </Button>
                                    </div>
                                </div>
                            </CardHeader>
                            <CardContent>
                                <div className="prose prose-sm dark:prose-invert max-w-none">
                                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                        {planResult}
                                    </ReactMarkdown>
                                </div>
                            </CardContent>
                        </Card>
                    )}

                    {/* Adjustment Result */}
                    {adjustResult && (
                        <Card>
                            <CardHeader>
                                <CardTitle className="text-lg">
                                    🔄 调整结果
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="prose prose-sm dark:prose-invert max-w-none">
                                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                        {adjustResult}
                                    </ReactMarkdown>
                                </div>
                            </CardContent>
                        </Card>
                    )}

                    {/* Adjustment Chat */}
                    {planResult && (
                        <Card>
                            <CardHeader>
                                <CardTitle className="text-lg">
                                    💬 追问调整
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="flex gap-2">
                                    <Input
                                        placeholder="对方案有任何问题或调整需求..."
                                        value={adjustInput}
                                        onChange={(e) =>
                                            setAdjustInput(e.target.value)
                                        }
                                        onKeyDown={(e) => {
                                            if (
                                                e.key === "Enter" &&
                                                !e.shiftKey
                                            ) {
                                                e.preventDefault();
                                                handleAdjust();
                                            }
                                        }}
                                        disabled={adjustLoading}
                                        className="flex-1"
                                    />
                                    <Button
                                        onClick={handleAdjust}
                                        disabled={
                                            adjustLoading || !adjustInput.trim()
                                        }
                                        size="icon"
                                    >
                                        {adjustLoading ? (
                                            <Loader2 className="h-4 w-4 animate-spin" />
                                        ) : (
                                            <RefreshCw className="h-4 w-4" />
                                        )}
                                    </Button>
                                </div>
                            </CardContent>
                        </Card>
                    )}
                </div>
            </div>
        </div>
    );
}
