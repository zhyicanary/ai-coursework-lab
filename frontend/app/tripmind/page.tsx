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
    Cloud,
    Train,
    Hotel,
    ClipboardList,
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

interface AgentStatus {
    name: string;
    label: string;
    status: "pending" | "running" | "done" | "error";
    icon: React.ElementType;
    color: string;
}

const agentDefs: Omit<AgentStatus, "status">[] = [
    { name: "weather", label: "天气", icon: Cloud, color: "text-sky-500" },
    { name: "transport", label: "交通", icon: Train, color: "text-violet-500" },
    { name: "hotel", label: "住宿", icon: Hotel, color: "text-amber-500" },
    { name: "itinerary", label: "行程", icon: Calendar, color: "text-emerald-500" },
    { name: "budget", label: "预算", icon: Banknote, color: "text-rose-500" },
];

const preferencesList = [
    { key: "culture", label: "文化", icon: Heart },
    { key: "food", label: "美食", icon: CoffeeIcon },
    { key: "nature", label: "自然", icon: TreePine },
    { key: "shopping", label: "购物", icon: ShoppingBag },
    { key: "leisure", label: "休闲", icon: Umbrella },
];

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
    const [adjustAgents, setAdjustAgents] = useState<string[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [copied, setCopied] = useState(false);
    const [lastState, setLastState] = useState<Record<string, unknown> | null>(
        null,
    );
    const resultRef = useRef<HTMLDivElement>(null);

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

    useEffect(() => {
        if (planResult) {
            localStorage.setItem(
                STORAGE_KEY,
                JSON.stringify({ planResult, adjustResult, lastState, adjustAgents }),
            );
        }
    }, [planResult, adjustResult, lastState]);

    const togglePreference = (key: string) => {
        setPreferences((prev) =>
            prev.includes(key) ? prev.filter((p) => p !== key) : [...prev, key],
        );
    };

    const inferAffectedAgents = (instruction: string): string[] => {
        const kw = instruction.toLowerCase();
        const agents = new Set<string>();
        const patterns: [string[], string[]][] = [
            [["酒店", "住宿", "民宿", "旅馆", "住"], ["hotel"]],
            [["预算", "加钱", "省钱", "便宜", "涨价", "降价", "提高预算", "增加预算", "减少预算", "节省"], ["hotel", "budget"]],
            [["行程", "景点", "想去", "玩", "参观", "游览", "偏好", "美食", "文化", "自然", "喜欢"], ["itinerary"]],
            [["交通", "飞机", "高铁", "动车", "航班", "火车", "打车", "自驾"], ["transport"]],
            [["天气"], ["weather"]],
            [["天数", "延长", "缩短", "增加一天", "减少一天", "多一天", "少一天"], ["weather", "hotel", "itinerary"]],
            [["目的地", "城市", "换个", "改到", "改成", "去", "换个地方"], ["weather", "transport", "hotel", "itinerary"]],
        ];
        for (const [keywords, keys] of patterns) {
            if (keywords.some((k) => kw.includes(k))) {
                keys.forEach((k) => agents.add(k));
            }
        }
        if (agents.size > 0 && !(agents.size === 1 && agents.has("weather"))) {
            agents.add("budget");
        }
        if (agents.size === 0) {
            agents.add("itinerary");
            agents.add("budget");
        }
        return Array.from(agents);
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

        const guessedAgents = inferAffectedAgents(text);
        setAdjustAgents(guessedAgents);
        setAgentStatuses((prev) =>
            prev.map((a) =>
                guessedAgents.includes(a.name) ? { ...a, status: "running" } : a,
            ),
        );

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
                setAgentStatuses((prev) =>
                    prev.map((a) =>
                        guessedAgents.includes(a.name) ? { ...a, status: "done" } : a,
                    ),
                );
                setTimeout(() => {
                    setAgentStatuses(prev =>
                        prev.map(a => a.status === "done" ? { ...a, status: "pending" } : a)
                    );
                    setAdjustAgents([]);
                }, 3000);
            }
            setAdjustResult(text);
        } catch (err) {
            setError(err instanceof Error ? err.message : "调整请求失败");
            setAgentStatuses((prev) =>
                prev.map((a) =>
                    guessedAgents.includes(a.name) ? { ...a, status: "error" } : a,
                ),
            );
        } finally {
            setAdjustLoading(false);
        }
    };

    const buildFullReport = useCallback(() => {
        const date = new Date().toLocaleString("zh-CN");
        const lines = [
            `# 旅行方案 — ${destination || "未指定目的地"}`,
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
            lines.push(``, `---`, `## 调整记录`, ``, `> ${adjustResult}`, ``);
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

    const statusConfig: Record<
        string,
        { bg: string; border: string; text: string; dot: string; label: string }
    > = {
        pending: {
            bg: "",
            border: "border-border",
            text: "text-muted-foreground",
            dot: "bg-muted-foreground/30",
            label: "等待中",
        },
        running: {
            bg: "bg-sky-500/5",
            border: "border-sky-500/40",
            text: "text-sky-500",
            dot: "bg-sky-500 animate-pulse",
            label: "执行中",
        },
        done: {
            bg: "bg-emerald-500/5",
            border: "border-emerald-500/40",
            text: "text-emerald-500",
            dot: "bg-emerald-500",
            label: "完成",
        },
        error: {
            bg: "bg-rose-500/5",
            border: "border-rose-500/40",
            text: "text-rose-500",
            dot: "bg-rose-500",
            label: "失败",
        },
    };

    return (
        <div className="scrollbar-thin overflow-auto p-4 md:p-8">
            <div className="max-w-4xl mx-auto space-y-6">
                {/* Header */}
                <div className="flex items-center gap-3 animate-fade-in">
                    <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-500/15 to-teal-500/15 ring-1 ring-cyan-500/20">
                        <Plane className="h-5 w-5 text-cyan-600 dark:text-cyan-400" />
                    </div>
                    <div>
                        <div className="flex items-center gap-2">
                            <h1 className="text-2xl font-bold">
                                TripMind 旅游规划
                            </h1>
                            <Badge variant="secondary" className="gap-1">
                                Multi-Agent
                            </Badge>
                        </div>
                        <p className="text-sm text-muted-foreground">
                            填写旅行需求，6 个专业 Agent 并行协作生成方案
                        </p>
                    </div>
                </div>

                {/* Form Card */}
                <Card className="animate-fade-in-up overflow-hidden">
                    <CardHeader className="bg-muted/30 border-b">
                        <CardTitle className="text-base flex items-center gap-2">
                            <ClipboardList className="h-4 w-4 text-muted-foreground" />
                            旅行需求
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4 pt-4">
                        <div className="grid gap-4 md:grid-cols-2">
                            <div className="space-y-2">
                                <Label htmlFor="destination">目的地</Label>
                                <div className="relative">
                                    <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                    <Input
                                        id="destination"
                                        className="pl-9"
                                        placeholder="例如：北京"
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
                                        placeholder="例如：上海"
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
                                <div className="relative">
                                    <Banknote className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                    <Input
                                        id="budget"
                                        type="number"
                                        min={500}
                                        step={100}
                                        className="pl-9"
                                        value={budget}
                                        onChange={(e) =>
                                            setBudget(Number(e.target.value))
                                        }
                                    />
                                </div>
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
                                                "inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm font-medium transition-all",
                                                active
                                                    ? "bg-primary text-primary-foreground border-primary shadow-sm"
                                                    : "bg-background hover:bg-accent hover:text-accent-foreground border-border",
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
                            {planning ? "Agent 协作中..." : "开始规划"}
                        </Button>
                    </CardContent>
                </Card>

                {/* Error */}
                {error && (
                    <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
                        {error}
                        <button
                            className="ml-2 underline"
                            onClick={() => setError(null)}
                        >
                            关闭
                        </button>
                    </div>
                )}

                {/* Agent Status Panel — Visual Progress Timeline */}
                {(planning || adjustLoading) && (
                    <Card className="animate-fade-in-up overflow-hidden">
                        <CardHeader className="bg-muted/30 border-b pb-3">
                            <CardTitle className="text-base flex items-center gap-2">
                                <Loader2 className="h-4 w-4 animate-spin text-primary" />
                                Agent 执行状态
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="pt-4">
                            {/* Horizontal progress bar */}
                            <div className="mb-4 flex items-center gap-1">
                                {agentStatuses.map((agent, i) => {
                                    const cfg = statusConfig[agent.status];
                                    return (
                                        <div key={agent.name} className="flex flex-1 items-center">
                                            <div
                                                className={cn(
                                                    "h-1.5 flex-1 rounded-full transition-all duration-500",
                                                    agent.status === "done"
                                                        ? "bg-emerald-500"
                                                        : agent.status === "running"
                                                          ? "bg-sky-500"
                                                          : agent.status === "error"
                                                            ? "bg-rose-500"
                                                            : "bg-muted",
                                                )}
                                            />
                                            {i < agentStatuses.length - 1 && (
                                                <div className="w-1" />
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                            {/* Agent cards */}
                            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
                                {agentStatuses.map((agent) => {
                                    const Icon = agent.icon;
                                    const cfg = statusConfig[agent.status];
                                    return (
                                        <div
                                            key={agent.name}
                                            className={cn(
                                                "flex flex-col items-center gap-1.5 rounded-lg border p-3 transition-all",
                                                cfg.bg,
                                                cfg.border,
                                            )}
                                        >
                                            <Icon className={cn("h-5 w-5", agent.color)} />
                                            <p className="text-xs font-medium">
                                                {agent.label}
                                            </p>
                                            <div className={cn("flex items-center gap-1.5 text-xs", cfg.text)}>
                                                <span className={cn("inline-block h-1.5 w-1.5 rounded-full", cfg.dot)} />
                                                {cfg.label}
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
                    <Card ref={resultRef} className="animate-fade-in-up overflow-hidden">
                        <CardHeader className="bg-muted/30 border-b">
                            <div className="flex items-center justify-between gap-2 flex-wrap">
                                <div className="flex items-center gap-2">
                                    <CardTitle className="text-base">
                                        旅行方案
                                    </CardTitle>
                                    {adjustResult && (
                                        <Badge variant="outline" className="gap-1 text-xs">
                                            <RefreshCw className="h-3 w-3" />
                                            已调整
                                        </Badge>
                                    )}
                                </div>
                                <div className="flex gap-1.5">
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        className="gap-1.5 h-8"
                                        onClick={handleDownloadMarkdown}
                                    >
                                        <Download className="h-3.5 w-3.5" />
                                        MD
                                    </Button>
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        className="gap-1.5 h-8"
                                        onClick={handleDownloadText}
                                    >
                                        <FileText className="h-3.5 w-3.5" />
                                        TXT
                                    </Button>
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        className="gap-1.5 h-8"
                                        onClick={handleCopyMarkdown}
                                    >
                                        {copied ? (
                                            <>
                                                <CheckCircle2 className="h-3.5 w-3.5" />
                                                已复制
                                            </>
                                        ) : (
                                            <>
                                                <FileText className="h-3.5 w-3.5" />
                                                复制
                                            </>
                                        )}
                                    </Button>
                                </div>
                            </div>
                        </CardHeader>
                        <CardContent className="pt-4">
                            <div className="prose prose-sm dark:prose-invert max-w-none">
                                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                    {planResult}
                                </ReactMarkdown>
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* Adjustment Chat */}
                {planResult && (
                    <Card className="animate-fade-in-up">
                        <CardHeader className="bg-muted/30 border-b pb-3">
                            <CardTitle className="text-base">
                                追问调整
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="pt-4">
                            <div className="flex gap-2">
                                <Input
                                    placeholder="例如：换个便宜点的酒店"
                                    value={adjustInput}
                                    onChange={(e) =>
                                        setAdjustInput(e.target.value)
                                    }
                                    onKeyDown={(e) => {
                                        if (e.key === "Enter" && !e.shiftKey) {
                                            e.preventDefault();
                                            handleAdjust();
                                        }
                                    }}
                                    disabled={adjustLoading}
                                    className="flex-1"
                                />
                                <Button
                                    onClick={handleAdjust}
                                    disabled={adjustLoading || !adjustInput.trim()}
                                    size="icon"
                                    className="h-10 w-10"
                                >
                                    {adjustLoading ? (
                                        <Loader2 className="h-4 w-4 animate-spin" />
                                    ) : (
                                        <RefreshCw className="h-4 w-4" />
                                    )}
                                </Button>
                            </div>
                            <p className="text-xs text-muted-foreground mt-2">
                                支持调整酒店、交通、行程、预算等，系统将仅重算受影响的 Agent
                            </p>
                        </CardContent>
                    </Card>
                )}
            </div>
        </div>
    );
}
