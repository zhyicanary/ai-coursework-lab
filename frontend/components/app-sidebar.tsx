"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
    Brain,
    Search,
    Plane,
    Settings,
    Sparkles,
    Github,
} from "lucide-react";

import {
    Sidebar,
    SidebarContent,
    SidebarFooter,
    SidebarGroup,
    SidebarGroupContent,
    SidebarGroupLabel,
    SidebarHeader,
    SidebarMenu,
    SidebarMenuButton,
    SidebarMenuItem,
    SidebarSeparator,
} from "@/components/ui/sidebar";

const navMain = [
    { href: "/", label: "首页", icon: Brain, desc: "项目概览" },
];

const navProjects = [
    {
        href: "/knowseeker",
        label: "KnowSeeker",
        icon: Search,
        desc: "Agentic RAG",
    },
    {
        href: "/tripmind",
        label: "TripMind",
        icon: Plane,
        desc: "Multi-Agent",
    },
];

const navSystem = [
    { href: "/settings", label: "设置", icon: Settings, desc: "LLM 配置" },
];

export function AppSidebar() {
    const pathname = usePathname();

    const allItems = [...navMain, ...navProjects, ...navSystem];

    return (
        <Sidebar collapsible="icon" variant="inset">
            <SidebarHeader>
                <SidebarMenu>
                    <SidebarMenuItem>
                        <SidebarMenuButton size="lg" asChild>
                            <Link href="/">
                                <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500 to-blue-500 text-primary-foreground">
                                    <Brain className="size-4" />
                                </div>
                                <div className="flex flex-col gap-0.5 leading-none">
                                    <span className="font-semibold">
                                        AI Coursework Lab
                                    </span>
                                    <span className="text-xs text-muted-foreground">
                                        智能应用系统设计
                                    </span>
                                </div>
                            </Link>
                        </SidebarMenuButton>
                    </SidebarMenuItem>
                </SidebarMenu>
            </SidebarHeader>

            <SidebarContent>
                {/* 主导航 */}
                <SidebarGroup>
                    <SidebarGroupLabel>导航</SidebarGroupLabel>
                    <SidebarGroupContent>
                        <SidebarMenu>
                            {navMain.map((item) => {
                                const Icon = item.icon;
                                const isActive = pathname === item.href;
                                return (
                                    <SidebarMenuItem key={item.href}>
                                        <SidebarMenuButton
                                            asChild
                                            isActive={isActive}
                                            tooltip={item.label}
                                        >
                                            <Link href={item.href}>
                                                <Icon className="size-4" />
                                                <span>{item.label}</span>
                                            </Link>
                                        </SidebarMenuButton>
                                    </SidebarMenuItem>
                                );
                            })}
                        </SidebarMenu>
                    </SidebarGroupContent>
                </SidebarGroup>

                {/* 项目 */}
                <SidebarGroup>
                    <SidebarGroupLabel>项目</SidebarGroupLabel>
                    <SidebarGroupContent>
                        <SidebarMenu>
                            {navProjects.map((item) => {
                                const Icon = item.icon;
                                const isActive = pathname === item.href;
                                return (
                                    <SidebarMenuItem key={item.href}>
                                        <SidebarMenuButton
                                            asChild
                                            isActive={isActive}
                                            tooltip={item.label}
                                        >
                                            <Link href={item.href}>
                                                <Icon className="size-4" />
                                                <span>{item.label}</span>
                                                <span className="ml-auto text-xs text-muted-foreground group-data-[collapsible=icon]:hidden">
                                                    {item.desc}
                                                </span>
                                            </Link>
                                        </SidebarMenuButton>
                                    </SidebarMenuItem>
                                );
                            })}
                        </SidebarMenu>
                    </SidebarGroupContent>
                </SidebarGroup>

                {/* 系统 */}
                <SidebarGroup>
                    <SidebarGroupLabel>系统</SidebarGroupLabel>
                    <SidebarGroupContent>
                        <SidebarMenu>
                            {navSystem.map((item) => {
                                const Icon = item.icon;
                                const isActive = pathname === item.href;
                                return (
                                    <SidebarMenuItem key={item.href}>
                                        <SidebarMenuButton
                                            asChild
                                            isActive={isActive}
                                            tooltip={item.label}
                                        >
                                            <Link href={item.href}>
                                                <Icon className="size-4" />
                                                <span>{item.label}</span>
                                            </Link>
                                        </SidebarMenuButton>
                                    </SidebarMenuItem>
                                );
                            })}
                        </SidebarMenu>
                    </SidebarGroupContent>
                </SidebarGroup>
            </SidebarContent>

            <SidebarFooter>
                <SidebarSeparator />
                <SidebarMenu>
                    <SidebarMenuItem>
                        <SidebarMenuButton asChild tooltip="技术栈">
                            <a
                                href="https://ui.shadcn.com"
                                target="_blank"
                                rel="noreferrer"
                            >
                                <Sparkles className="size-4" />
                                <span>shadcn/ui</span>
                            </a>
                        </SidebarMenuButton>
                    </SidebarMenuItem>
                    <SidebarMenuItem>
                        <div className="flex items-center justify-between px-2 py-1 text-xs text-muted-foreground group-data-[collapsible=icon]:hidden">
                            <span>v1.0 · 2026</span>
                        </div>
                    </SidebarMenuItem>
                </SidebarMenu>
            </SidebarFooter>
        </Sidebar>
    );
}
