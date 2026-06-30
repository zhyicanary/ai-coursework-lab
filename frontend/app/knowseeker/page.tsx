"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import {
    Search,
    Send,
    Upload,
    Trash2,
    FileText,
    Loader2,
    Brain,
    ChevronDown,
    ChevronUp,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const API_BASE = "http://localhost:8000";

interface Document {
    id: string;
    doc_id: string;
    file_name: string;
    chunks_count: number;
}

interface ChatMessage {
    role: "user" | "assistant";
    content: string;
    thinking_trace?: { step: string; content: string; detail?: string }[];
    citations?: { doc_name: string; content?: string }[];
}

interface AgentState {
    thinking_trace: { step: string; content: string; detail?: string }[];
    citations: { doc_name: string; content?: string }[];
}

export default function KnowSeekerPage() {
    const [documents, setDocuments] = useState<Document[]>([]);
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [expandedThinking, setExpandedThinking] = useState<
        Record<number, boolean>
    >({});
    const fileInputRef = useRef<HTMLInputElement>(null);
    const chatEndRef = useRef<HTMLDivElement>(null);

    const fetchDocuments = useCallback(async () => {
        try {
            const res = await fetch(`${API_BASE}/api/documents`);
            if (res.ok) {
                const data = await res.json();
                setDocuments(data);
            }
        } catch {
            // Backend not available yet
        }
    }, []);

    useEffect(() => {
        fetchDocuments();
    }, [fetchDocuments]);

    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        setUploading(true);
        setError(null);

        try {
            const formData = new FormData();
            formData.append("file", file);

            const res = await fetch(`${API_BASE}/api/documents/upload`, {
                method: "POST",
                body: formData,
            });

            if (!res.ok) {
                const errData = await res.json();
                throw new Error(errData.detail || "Upload failed");
            }

            await fetchDocuments();
        } catch (err) {
            setError(err instanceof Error ? err.message : "Upload failed");
        } finally {
            setUploading(false);
            if (fileInputRef.current) fileInputRef.current.value = "";
        }
    };

    const handleDelete = async (docId: string) => {
        try {
            const res = await fetch(`${API_BASE}/api/documents/${docId}`, {
                method: "DELETE",
            });
            if (res.ok) {
                await fetchDocuments();
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : "Delete failed");
        }
    };

    const handleSend = async () => {
        const question = input.trim();
        if (!question || loading) return;

        setInput("");
        setError(null);

        const userMsg: ChatMessage = { role: "user", content: question };
        setMessages((prev) => [...prev, userMsg]);
        setLoading(true);

        try {
            const res = await fetch(`${API_BASE}/api/chat`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ question }),
            });

            if (!res.ok) {
                throw new Error("Chat request failed");
            }

            const data = await res.json();

            const assistantMsg: ChatMessage = {
                role: "assistant",
                content: data.answer || "（未能生成回答）",
                thinking_trace: data.thinking_trace || [],
                citations: data.citations || [],
            };

            setMessages((prev) => [...prev, assistantMsg]);
        } catch (err) {
            const errorMsg: ChatMessage = {
                role: "assistant",
                content: `❌ 请求失败：${err instanceof Error ? err.message : "未知错误"}`,
            };
            setMessages((prev) => [...prev, errorMsg]);
        } finally {
            setLoading(false);
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const toggleThinking = (idx: number) => {
        setExpandedThinking((prev) => ({ ...prev, [idx]: !prev[idx] }));
    };

    const iconMap: Record<string, string> = {
        analyze: "📋",
        retrieve: "🔍",
        evaluate: "📊",
        reformulate: "🔄",
        generate: "📝",
    };

    return (
        <div className="flex h-full">
            {/* Left Sidebar - Document Management */}
            <aside className="hidden lg:flex w-72 flex-col border-r bg-sidebar-background">
                <div className="p-4 border-b">
                    <h2 className="text-sm font-semibold flex items-center gap-2">
                        <FileText className="h-4 w-4" />
                        文档管理
                    </h2>
                </div>

                <div className="p-4">
                    <input
                        ref={fileInputRef}
                        type="file"
                        className="hidden"
                        onChange={handleUpload}
                        accept=".pdf,.txt,.md,.docx,.csv,.json,.xml"
                    />
                    <Button
                        variant="outline"
                        className="w-full gap-2"
                        onClick={() => fileInputRef.current?.click()}
                        disabled={uploading}
                    >
                        {uploading ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                            <Upload className="h-4 w-4" />
                        )}
                        {uploading ? "上传中..." : "上传文档"}
                    </Button>
                    <p className="text-xs text-muted-foreground mt-2">
                        支持 PDF, TXT, Markdown, DOCX 等格式
                    </p>
                </div>

                <Separator />

                <ScrollArea className="flex-1 p-4">
                    {documents.length === 0 ? (
                        <p className="text-sm text-muted-foreground text-center py-8">
                            暂无文档，请上传
                        </p>
                    ) : (
                        <div className="space-y-2">
                            {documents.map((doc) => (
                                <div
                                    key={doc.id || doc.doc_id}
                                    className="flex items-start justify-between rounded-md border p-3 text-sm"
                                >
                                    <div className="flex-1 min-w-0">
                                        <p className="font-medium truncate">
                                            {doc.file_name}
                                        </p>
                                        <p className="text-xs text-muted-foreground">
                                            {doc.chunks_count} 个片段
                                        </p>
                                    </div>
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        className="h-7 w-7 text-muted-foreground hover:text-destructive shrink-0"
                                        onClick={() => handleDelete(doc.doc_id)}
                                    >
                                        <Trash2 className="h-4 w-4" />
                                    </Button>
                                </div>
                            ))}
                        </div>
                    )}
                </ScrollArea>
            </aside>

            {/* Main Chat Area */}
            <div className="flex flex-1 flex-col">
                {/* Header */}
                <div className="flex items-center gap-2 border-b px-4 py-3">
                    <Brain className="h-5 w-5 text-primary" />
                    <h1 className="text-lg font-semibold">KnowSeeker</h1>
                    <Badge variant="secondary" className="ml-2 text-xs">
                        Agentic RAG
                    </Badge>
                </div>

                {/* Chat Messages */}
                <ScrollArea className="flex-1 px-4">
                    {messages.length === 0 ? (
                        <div className="flex flex-col items-center justify-center h-full text-center py-16">
                            <Search className="h-12 w-12 text-muted-foreground mb-4" />
                            <h2 className="text-xl font-semibold mb-2">
                                Agentic RAG 知识助手
                            </h2>
                            <p className="text-muted-foreground max-w-md">
                                上传文档后即可开始提问。AI Agent
                                会自主分析问题、 制定检索策略并生成精准回答。
                            </p>
                        </div>
                    ) : (
                        <div className="space-y-6 py-4">
                            {messages.map((msg, idx) => (
                                <div
                                    key={idx}
                                    className={cn(
                                        "flex gap-3",
                                        msg.role === "user"
                                            ? "justify-end"
                                            : "justify-start",
                                    )}
                                >
                                    <div
                                        className={cn(
                                            "max-w-[80%] rounded-lg px-4 py-3",
                                            msg.role === "user"
                                                ? "bg-primary text-primary-foreground"
                                                : "bg-muted",
                                        )}
                                    >
                                        <div className="text-sm whitespace-pre-wrap">
                                            {msg.content}
                                        </div>

                                        {/* Thinking Process */}
                                        {msg.role === "assistant" &&
                                            msg.thinking_trace &&
                                            msg.thinking_trace.length > 0 && (
                                                <div className="mt-3 border-t pt-3">
                                                    <button
                                                        className="flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
                                                        onClick={() =>
                                                            toggleThinking(idx)
                                                        }
                                                    >
                                                        {expandedThinking[
                                                            idx
                                                        ] ? (
                                                            <ChevronUp className="h-3 w-3" />
                                                        ) : (
                                                            <ChevronDown className="h-3 w-3" />
                                                        )}
                                                        🧠 思考过程
                                                    </button>
                                                    {expandedThinking[idx] && (
                                                        <div className="mt-2 space-y-2">
                                                            {msg.thinking_trace.map(
                                                                (step, si) => (
                                                                    <div
                                                                        key={si}
                                                                        className="text-xs"
                                                                    >
                                                                        <p className="font-medium">
                                                                            {iconMap[
                                                                                step
                                                                                    .step
                                                                            ] ||
                                                                                "🤖"}{" "}
                                                                            {
                                                                                step.content
                                                                            }
                                                                        </p>
                                                                        {step.detail && (
                                                                            <p className="text-muted-foreground mt-0.5 ml-5">
                                                                                {
                                                                                    step.detail
                                                                                }
                                                                            </p>
                                                                        )}
                                                                    </div>
                                                                ),
                                                            )}
                                                        </div>
                                                    )}
                                                </div>
                                            )}

                                        {/* Citations */}
                                        {msg.role === "assistant" &&
                                            msg.citations &&
                                            msg.citations.length > 0 && (
                                                <div className="mt-3 border-t pt-3">
                                                    <p className="text-xs font-medium text-muted-foreground mb-1">
                                                        📎 引用来源
                                                    </p>
                                                    {msg.citations.map(
                                                        (c, ci) => (
                                                            <p
                                                                key={ci}
                                                                className="text-xs text-muted-foreground bg-background/50 rounded px-2 py-1 mt-1"
                                                            >
                                                                {c.doc_name}
                                                            </p>
                                                        ),
                                                    )}
                                                </div>
                                            )}
                                    </div>
                                </div>
                            ))}
                            {loading && (
                                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                    <Loader2 className="h-4 w-4 animate-spin" />
                                    Agent 正在思考...
                                </div>
                            )}
                            <div ref={chatEndRef} />
                        </div>
                    )}
                </ScrollArea>

                {/* Error */}
                {error && (
                    <div className="mx-4 mb-2 rounded-md bg-destructive/10 px-4 py-2 text-sm text-destructive">
                        {error}
                        <button
                            className="ml-2 underline"
                            onClick={() => setError(null)}
                        >
                            关闭
                        </button>
                    </div>
                )}

                {/* Input Area */}
                <div className="border-t p-4">
                    <div className="flex gap-2">
                        <Input
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder="请输入您的问题... (Enter 发送)"
                            disabled={loading}
                            className="flex-1"
                        />
                        <Button
                            onClick={handleSend}
                            disabled={loading || !input.trim()}
                            size="icon"
                        >
                            {loading ? (
                                <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                                <Send className="h-4 w-4" />
                            )}
                        </Button>
                    </div>
                </div>
            </div>
        </div>
    );
}
