"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { toast } from "sonner"
import {
  Cloud,
  Train,
  Hotel,
  Calendar,
  Banknote,
  Heart,
  Coffee as CoffeeIcon,
  TreePine,
  ShoppingBag,
  Umbrella,
  Send,
  Download,
  Copy,
  Check,
  Sparkles,
  AlertCircle,
  Loader2,
  Plane,
  MapPin,
  RefreshCw,
  FileText,
  FileDown,
  Wand2,
} from "lucide-react"
import type { LucideIcon } from "lucide-react"
import { API_BASE_API } from "@/lib/config"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Accordion,
  AccordionItem,
  AccordionTrigger,
  AccordionContent,
} from "@/components/ui/accordion"
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert"
import { Progress } from "@/components/ui/progress"
import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"

type AgentStatus = "pending" | "running" | "done" | "error"

interface AgentState {
  name: string
  status: AgentStatus
  data?: unknown
}

const agentDefs: { name: string; label: string; icon: LucideIcon; color: string }[] = [
  { name: "weather", label: "天气", icon: Cloud, color: "text-sky-500" },
  { name: "transport", label: "交通", icon: Train, color: "text-violet-500" },
  { name: "hotel", label: "住宿", icon: Hotel, color: "text-amber-500" },
  { name: "itinerary", label: "行程", icon: Calendar, color: "text-emerald-500" },
  { name: "budget", label: "预算", icon: Banknote, color: "text-rose-500" },
]

const preferencesList: { key: string; label: string; icon: LucideIcon }[] = [
  { key: "culture", label: "文化", icon: Heart },
  { key: "food", label: "美食", icon: CoffeeIcon },
  { key: "nature", label: "自然", icon: TreePine },
  { key: "shopping", label: "购物", icon: ShoppingBag },
  { key: "leisure", label: "休闲", icon: Umbrella },
]

const statusConfig: Record<
  AgentStatus,
  { label: string; text: string; border: string; bg: string; dot: string }
> = {
  pending: {
    label: "等待中",
    text: "text-muted-foreground",
    border: "border-border",
    bg: "bg-muted/40",
    dot: "bg-muted-foreground/40",
  },
  running: {
    label: "执行中",
    text: "text-sky-500",
    border: "border-sky-500/50",
    bg: "bg-sky-500/5",
    dot: "bg-sky-500",
  },
  done: {
    label: "完成",
    text: "text-emerald-500",
    border: "border-emerald-500/50",
    bg: "bg-emerald-500/5",
    dot: "bg-emerald-500",
  },
  error: {
    label: "失败",
    text: "text-rose-500",
    border: "border-rose-500/50",
    bg: "bg-rose-500/5",
    dot: "bg-rose-500",
  },
}

/**
 * Robust markdown styling via Tailwind arbitrary variants — works without
 * @tailwindcss/typography and keeps ReactMarkdown free of custom components.
 */
const markdownStyles =
  "[&_h1]:mt-5 [&_h1]:mb-3 [&_h1]:text-2xl [&_h1]:font-bold [&_h1]:tracking-tight " +
  "[&_h2]:mt-4 [&_h2]:mb-2 [&_h2]:text-xl [&_h2]:font-semibold " +
  "[&_h3]:mt-3 [&_h3]:mb-2 [&_h3]:text-lg [&_h3]:font-semibold " +
  "[&_h4]:mt-3 [&_h4]:mb-1 [&_h4]:font-semibold " +
  "[&_p]:mb-3 [&_p]:leading-7 [&_p]:text-muted-foreground " +
  "[&_ul]:mb-3 [&_ul]:ml-6 [&_ul]:list-disc [&_ul]:flex [&_ul]:flex-col [&_ul]:gap-1 " +
  "[&_ol]:mb-3 [&_ol]:ml-6 [&_ol]:list-decimal [&_ol]:flex [&_ol]:flex-col [&_ol]:gap-1 " +
  "[&_li]:leading-7 [&_li]:text-muted-foreground " +
  "[&_strong]:font-semibold [&_strong]:text-foreground " +
  "[&_blockquote]:my-3 [&_blockquote]:border-l-2 [&_blockquote]:border-primary [&_blockquote]:pl-4 [&_blockquote]:italic [&_blockquote]:text-muted-foreground " +
  "[&_code]:rounded [&_code]:bg-muted [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:text-sm [&_code]:font-mono " +
  "[&_pre]:mb-3 [&_pre]:overflow-x-auto [&_pre]:rounded-md [&_pre]:bg-muted [&_pre]:p-3 [&_pre]:text-sm " +
  "[&_pre_code]:bg-transparent [&_pre_code]:p-0 " +
  "[&_a]:text-primary [&_a]:underline [&_a]:underline-offset-4 " +
  "[&_table]:mb-3 [&_table]:w-full [&_table]:border-collapse [&_table]:text-sm " +
  "[&_th]:border [&_th]:border-border [&_th]:bg-muted [&_th]:px-3 [&_th]:py-1.5 [&_th]:text-left [&_th]:font-semibold " +
  "[&_td]:border [&_td]:border-border [&_td]:px-3 [&_td]:py-1.5 " +
  "[&_hr]:my-4 [&_hr]:border-border"

function inferAffectedAgents(message: string): string[] {
  const affected = new Set<string>()

  if (/酒店|住宿|民宿/.test(message)) affected.add("hotel")
  if (/预算|便宜|省钱/.test(message)) {
    affected.add("hotel")
    affected.add("budget")
  }
  if (/行程|景点|玩/.test(message)) affected.add("itinerary")
  if (/交通|飞机|高铁/.test(message)) affected.add("transport")
  if (/天气/.test(message)) affected.add("weather")
  if (/天数|延长|缩短/.test(message)) {
    affected.add("weather")
    affected.add("hotel")
    affected.add("itinerary")
  }
  if (/目的地|城市|换个/.test(message)) {
    affected.add("weather")
    affected.add("transport")
    affected.add("hotel")
    affected.add("itinerary")
  }

  // Always add budget if more than just weather affected.
  const nonWeather = [...affected].filter((a) => a !== "weather")
  if (nonWeather.length > 0) affected.add("budget")

  return [...affected]
}

const PLAN_STORAGE_KEY = "tripmind_plan"

export default function TripMindPage() {
  const [destination, setDestination] = useState("")
  const [departure, setDeparture] = useState("")
  const [days, setDays] = useState("")
  const [budget, setBudget] = useState("")
  const [preferences, setPreferences] = useState<string[]>([])

  const [planResult, setPlanResult] = useState<string | null>(null)
  const planResultRef = useRef<string | null>(null)
  const [agentStatuses, setAgentStatuses] = useState<AgentState[]>([])
  const [planning, setPlanning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [adjustInput, setAdjustInput] = useState("")
  const [adjustLoading, setAdjustLoading] = useState(false)
  const [adjustResult, setAdjustResult] = useState<string | null>(null)

  const [copied, setCopied] = useState(false)
  const [lastState, setLastState] = useState<Record<string, unknown> | null>(null)

  // Restore persisted plan on mount.
  useEffect(() => {
    try {
      const saved = localStorage.getItem(PLAN_STORAGE_KEY)
      if (saved) setPlanResult(saved)
    } catch {
      // ignore storage errors
    }
  }, [])

  // Persist plan whenever it changes.
  useEffect(() => {
    try {
      if (planResult) localStorage.setItem(PLAN_STORAGE_KEY, planResult)
      else localStorage.removeItem(PLAN_STORAGE_KEY)
    } catch {
      // ignore storage errors
    }
  }, [planResult])

  const completedCount = agentStatuses.filter((a) => a.status === "done").length
  const totalCount = agentStatuses.length
  const progressValue =
    totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0

  const handleStreamData = useCallback((data: Record<string, unknown>) => {
    const resultKeyToAgent: Record<string, string> = {
      weather_result: "weather",
      transport_result: "transport",
      hotel_result: "hotel",
      itinerary_result: "itinerary",
      budget_result: "budget",
    }

    for (const [key, agentName] of Object.entries(resultKeyToAgent)) {
      if (key in data) {
        setAgentStatuses((prev) => {
          const next = prev.map((a) =>
            a.name === agentName
              ? { ...a, status: "done" as AgentStatus, data: data[key] }
              : a
          )
          // Pre-mark the next pending agent (in defined order) as running.
          const idx = agentDefs.findIndex((a) => a.name === agentName)
          for (let i = idx + 1; i < agentDefs.length; i++) {
            const target = next.find((a) => a.name === agentDefs[i].name)
            if (target && target.status === "pending") {
              target.status = "running"
              break
            }
          }
          return next
        })
      }
    }

    if ("final_plan" in data && typeof data.final_plan === "string") {
      planResultRef.current = data.final_plan
      setPlanResult(data.final_plan)
    }
    if ("__full_state__" in data && data.__full_state__) {
      setLastState(data.__full_state__ as Record<string, unknown>)
    }
  }, [])

  const startPlanning = async () => {
    if (!destination.trim()) {
      toast.error("请输入目的地")
      return
    }

    setError(null)
    setPlanResult(null)
    setAdjustInput("")
    setAdjustResult(null)
    setPlanning(true)
    setAgentStatuses(
      agentDefs.map((a, i) => ({
        name: a.name,
        status: (i === 0 ? "running" : "pending") as AgentStatus,
      }))
    )

    try {
      const res = await fetch(`${API_BASE_API}/travel/plan/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          destination,
          departure_city: departure,
          days: Number(days) || 0,
          budget: Number(budget) || 0,
          preferences,
        }),
      })

      if (!res.ok || !res.body) {
        throw new Error(`请求失败（HTTP ${res.status}）`)
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ""

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split("\n")
        buffer = lines.pop() ?? ""
        for (const line of lines) {
          const trimmed = line.trim()
          if (!trimmed.startsWith("data:")) continue
          const jsonStr = trimmed.slice(5).trim()
          if (!jsonStr) continue
          try {
            handleStreamData(JSON.parse(jsonStr))
          } catch {
            // skip non-JSON keep-alive chunks
          }
        }
      }

      // Safety net: only mark as done if we received final_plan.
      // Otherwise the stream ended unexpectedly — mark as error.
      const gotFinalPlan = planResultRef.current !== null
      if (gotFinalPlan) {
        setAgentStatuses((prev) =>
          prev.map((a) =>
            a.status === "running" || a.status === "pending"
              ? { ...a, status: "done" as AgentStatus }
              : a
          )
        )
        toast.success("行程规划完成！")
      } else {
        setAgentStatuses((prev) =>
          prev.map((a) =>
            a.status === "running" || a.status === "pending"
              ? { ...a, status: "error" as AgentStatus }
              : a
          )
        )
        setError("流式连接异常结束，部分 Agent 未完成")
        toast.error("规划未完成 — 部分智能体执行失败")
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "规划失败，请稍后重试"
      setError(msg)
      setAgentStatuses((prev) =>
        prev.map((a) =>
          a.status === "running" ? { ...a, status: "error" as AgentStatus } : a
        )
      )
      toast.error(msg)
    } finally {
      setPlanning(false)
    }
  }

  const handleAdjust = async () => {
    if (!adjustInput.trim()) return
    if (!lastState) {
      toast.error("请先完成规划，再进行调整")
      return
    }

    setAdjustLoading(true)
    try {
      const res = await fetch(`${API_BASE_API}/travel/adjust`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ state: lastState, message: adjustInput }),
      })
      if (!res.ok) throw new Error(`调整失败（HTTP ${res.status}）`)

      const data = await res.json()
      if (typeof data.final_plan === "string") {
        setPlanResult(data.final_plan)
        setAdjustResult(data.final_plan)
        toast.success("行程已根据您的需求调整")
      }
      if (data.__full_state__) setLastState(data.__full_state__)
      else if (data.state) setLastState(data.state)

      setAdjustInput("")
    } catch (err) {
      const msg = err instanceof Error ? err.message : "调整失败，请重试"
      toast.error(msg)
    } finally {
      setAdjustLoading(false)
    }
  }

  const downloadFile = (content: string, filename: string, mime: string) => {
    const blob = new Blob([content], { type: mime })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    toast.success(`已下载 ${filename}`)
  }

  const handleDownloadMd = () => {
    if (!planResult) return
    downloadFile(planResult, `tripmind-${destination || "plan"}.md`, "text/markdown")
  }

  const handleDownloadTxt = () => {
    if (!planResult) return
    downloadFile(planResult, `tripmind-${destination || "plan"}.txt`, "text/plain")
  }

  const handleCopy = async () => {
    if (!planResult) return
    try {
      await navigator.clipboard.writeText(planResult)
      setCopied(true)
      toast.success("已复制到剪贴板")
      setTimeout(() => setCopied(false), 2000)
    } catch {
      toast.error("复制失败，请手动选择文本复制")
    }
  }

  const togglePreference = (key: string) => {
    setPreferences((prev) =>
      prev.includes(key) ? prev.filter((p) => p !== key) : [...prev, key]
    )
  }

  const affectedAgents = adjustInput.trim() ? inferAffectedAgents(adjustInput) : []

  return (
    <div className="mx-auto min-h-screen w-full max-w-5xl px-4 py-8 sm:py-10">
      <div className="flex flex-col gap-6">
        {/* Header */}
        <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex size-12 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-sm">
              <Plane className="size-6" />
            </div>
            <div className="flex flex-col">
              <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">
                TripMind
              </h1>
              <p className="text-sm text-muted-foreground">
                智能多代理旅行规划助手
              </p>
            </div>
          </div>
          <Badge variant="secondary" className="w-fit gap-1.5 px-3 py-1 text-sm">
            <Sparkles />
            Multi-Agent
          </Badge>
        </header>

        {/* Travel Form */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <MapPin className="size-5 text-primary" />
              行程信息
            </CardTitle>
            <CardDescription>
              填写旅行偏好，5 个专业代理将协同为您规划最佳行程
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col gap-5">
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="flex flex-col gap-2">
                  <Label htmlFor="destination">
                    目的地 <span className="text-destructive">*</span>
                  </Label>
                  <Input
                    id="destination"
                    placeholder="例如：东京"
                    value={destination}
                    onChange={(e) => setDestination(e.target.value)}
                  />
                </div>
                <div className="flex flex-col gap-2">
                  <Label htmlFor="departure">出发城市</Label>
                  <Input
                    id="departure"
                    placeholder="例如：上海"
                    value={departure}
                    onChange={(e) => setDeparture(e.target.value)}
                  />
                </div>
                <div className="flex flex-col gap-2">
                  <Label htmlFor="days">旅行天数</Label>
                  <Input
                    id="days"
                    type="number"
                    min={1}
                    placeholder="例如：5"
                    value={days}
                    onChange={(e) => setDays(e.target.value)}
                  />
                </div>
                <div className="flex flex-col gap-2">
                  <Label htmlFor="budget">预算（元）</Label>
                  <Input
                    id="budget"
                    type="number"
                    min={0}
                    placeholder="例如：8000"
                    value={budget}
                    onChange={(e) => setBudget(e.target.value)}
                  />
                </div>
              </div>

              <Separator />

              <div className="flex flex-col gap-2.5">
                <Label>偏好类型</Label>
                <div className="flex flex-wrap gap-2">
                  {preferencesList.map((pref) => {
                    const active = preferences.includes(pref.key)
                    const PrefIcon = pref.icon
                    return (
                      <Button
                        key={pref.key}
                        type="button"
                        variant={active ? "default" : "outline"}
                        size="sm"
                        onClick={() => togglePreference(pref.key)}
                      >
                        <PrefIcon data-icon="inline-start" />
                        {pref.label}
                      </Button>
                    )
                  })}
                </div>
              </div>
            </div>
          </CardContent>
          <CardFooter>
            <Button
              className="w-full"
              size="lg"
              onClick={startPlanning}
              disabled={planning}
            >
              {planning ? (
                <>
                  <Loader2 className="animate-spin" data-icon="inline-start" />
                  规划中…
                </>
              ) : (
                <>
                  <Wand2 data-icon="inline-start" />
                  开始规划
                </>
              )}
            </Button>
          </CardFooter>
        </Card>

        {/* Agent Status Panel */}
        {agentStatuses.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="size-5 text-primary" />
                代理执行状态
              </CardTitle>
              <CardDescription>
                {planning
                  ? "5 个代理正在协同工作，请稍候"
                  : "本次规划涉及的代理及执行结果"}
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-5">
              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">整体进度</span>
                  <span className="font-medium tabular-nums">
                    {completedCount}/{totalCount} · {progressValue}%
                  </span>
                </div>
                <Progress value={progressValue} />
              </div>

              <Separator />

              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
                {agentDefs.map((agent) => {
                  const status =
                    agentStatuses.find((a) => a.name === agent.name)?.status ??
                    "pending"
                  const config = statusConfig[status]
                  const AgentIcon = agent.icon
                  return (
                    <div
                      key={agent.name}
                      className={cn(
                        "flex flex-col items-center gap-2 rounded-xl border p-4 text-center transition-colors",
                        config.border,
                        config.bg
                      )}
                    >
                      <div className="relative">
                        <AgentIcon
                          className={cn(
                            "size-7",
                            agent.color,
                            status === "running" && "animate-pulse"
                          )}
                        />
                        <span
                          className={cn(
                            "absolute -right-1 -top-1 size-2.5 rounded-full ring-2 ring-background",
                            config.dot,
                            status === "running" && "animate-pulse"
                          )}
                        />
                      </div>
                      <span className="text-sm font-medium">{agent.label}</span>
                      <Badge variant="outline" className={cn("text-xs", config.text)}>
                        {config.label}
                      </Badge>
                    </div>
                  )
                })}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Error */}
        {error && (
          <Alert variant="destructive">
            <AlertCircle />
            <AlertTitle>规划出错</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Loading skeleton */}
        {planning && !planResult && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="size-5 text-primary" />
                正在生成行程方案…
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              <Skeleton className="h-6 w-2/3" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-5/6" />
              <Skeleton className="h-24 w-full" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-4/6" />
            </CardContent>
          </Card>
        )}

        {/* Plan Result */}
        {planResult && (
          <Card>
            <CardHeader>
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div className="flex flex-col gap-1">
                  <CardTitle className="flex items-center gap-2">
                    <FileText className="size-5 text-primary" />
                    行程方案
                    {adjustResult && (
                      <Badge variant="secondary" className="text-xs">
                        已根据反馈调整
                      </Badge>
                    )}
                  </CardTitle>
                  <CardDescription>
                    由多代理协同生成的完整旅行计划
                  </CardDescription>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button variant="outline" size="sm" onClick={handleCopy}>
                    {copied ? (
                      <Check data-icon="inline-start" />
                    ) : (
                      <Copy data-icon="inline-start" />
                    )}
                    {copied ? "已复制" : "复制"}
                  </Button>
                  <Button variant="outline" size="sm" onClick={handleDownloadMd}>
                    <FileDown data-icon="inline-start" />
                    Markdown
                  </Button>
                  <Button variant="outline" size="sm" onClick={handleDownloadTxt}>
                    <Download data-icon="inline-start" />
                    TXT
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[600px] w-full rounded-lg border p-5">
                <div className={cn("max-w-none text-sm", markdownStyles)}>
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {planResult}
                  </ReactMarkdown>
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        )}

        {/* Agent Details Accordion */}
        {agentStatuses.some((a) => a.data !== undefined) && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="size-5 text-primary" />
                代理工作详情
              </CardTitle>
              <CardDescription>展开查看每个代理的实时输出结果</CardDescription>
            </CardHeader>
            <CardContent>
              <Accordion type="single" collapsible className="w-full">
                {agentDefs.map((agent) => {
                  const state = agentStatuses.find((a) => a.name === agent.name)
                  if (!state || state.data === undefined) return null
                  const AgentIcon = agent.icon
                  const config = statusConfig[state.status]
                  return (
                    <AccordionItem key={agent.name} value={agent.name}>
                      <AccordionTrigger className="hover:no-underline">
                        <span className="flex items-center gap-2">
                          <AgentIcon className={cn("size-4", agent.color)} />
                          <span className="font-medium">{agent.label}</span>
                          <Badge
                            variant="outline"
                            className={cn("text-xs", config.text)}
                          >
                            {config.label}
                          </Badge>
                        </span>
                      </AccordionTrigger>
                      <AccordionContent>
                        <pre className="overflow-x-auto rounded-md bg-muted p-3 text-xs leading-relaxed text-muted-foreground">
                          {JSON.stringify(state.data, null, 2)}
                        </pre>
                      </AccordionContent>
                    </AccordionItem>
                  )
                })}
              </Accordion>
            </CardContent>
          </Card>
        )}

        {/* Adjustment */}
        {planResult && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <RefreshCw className="size-5 text-primary" />
                调整行程
              </CardTitle>
              <CardDescription>
                输入修改需求，相关代理将重新规划（Ctrl/⌘ + Enter 发送）
              </CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col gap-3">
              {affectedAgents.length > 0 && (
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm text-muted-foreground">影响代理：</span>
                  {affectedAgents.map((name) => {
                    const def = agentDefs.find((a) => a.name === name)
                    return def ? (
                      <Badge
                        key={name}
                        variant="secondary"
                        className={cn("text-xs", def.color)}
                      >
                        {def.label}
                      </Badge>
                    ) : null
                  })}
                </div>
              )}
              <Textarea
                placeholder="例如：把预算减少到 5000，换一家更便宜的酒店"
                value={adjustInput}
                onChange={(e) => setAdjustInput(e.target.value)}
                rows={3}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                    e.preventDefault()
                    handleAdjust()
                  }
                }}
              />
            </CardContent>
            <CardFooter>
              <Button
                className="w-full"
                onClick={handleAdjust}
                disabled={adjustLoading || !adjustInput.trim()}
              >
                {adjustLoading ? (
                  <>
                    <Loader2 className="animate-spin" data-icon="inline-start" />
                    调整中…
                  </>
                ) : (
                  <>
                    发送调整
                    <Send data-icon="inline-end" />
                  </>
                )}
              </Button>
            </CardFooter>
          </Card>
        )}

        <footer className="flex items-center justify-center py-2">
          <p className="text-xs text-muted-foreground">
            TripMind · Multi-Agent Travel Planner · Powered by Next.js and
            shadcn/ui
          </p>
        </footer>
      </div>
    </div>
  )
}
