"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Brain, Search, Plane, Settings, Moon, Sun } from "lucide-react";
import { useState, useEffect } from "react";

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
} from "@/components/ui/sidebar";
import { Button } from "@/components/ui/button";

const navItems = [
    { href: "/", label: "Home", icon: Brain },
    { href: "/knowseeker", label: "KnowSeeker", icon: Search },
    { href: "/tripmind", label: "TripMind", icon: Plane },
    { href: "/settings", label: "Settings", icon: Settings },
];

function ThemeToggle() {
    const [dark, setDark] = useState(false);

    useEffect(() => {
        const stored = localStorage.getItem("theme");
        if (
            stored === "dark" ||
            (!stored &&
                window.matchMedia("(prefers-color-scheme: dark)").matches)
        ) {
            setDark(true);
            document.documentElement.classList.add("dark");
        }
    }, []);

    const toggle = () => {
        setDark((prev) => {
            const next = !prev;
            if (next) {
                document.documentElement.classList.add("dark");
                localStorage.setItem("theme", "dark");
            } else {
                document.documentElement.classList.remove("dark");
                localStorage.setItem("theme", "light");
            }
            return next;
        });
    };

    return (
        <Button
            variant="ghost"
            size="icon"
            onClick={toggle}
            title={dark ? "Switch to light" : "Switch to dark"}
        >
            {dark ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
        </Button>
    );
}

export function AppSidebar() {
    const pathname = usePathname();

    return (
        <Sidebar collapsible="icon" variant="sidebar">
            <SidebarHeader>
                <SidebarMenu>
                    <SidebarMenuItem>
                        <SidebarMenuButton size="lg" asChild>
                            <Link href="/">
                                <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                                    <Brain className="size-4" />
                                </div>
                                <div className="flex flex-col gap-0.5 leading-none">
                                    <span className="font-semibold">AI Lab</span>
                                    <span className="text-xs text-muted-foreground">
                                        Coursework
                                    </span>
                                </div>
                            </Link>
                        </SidebarMenuButton>
                    </SidebarMenuItem>
                </SidebarMenu>
            </SidebarHeader>
            <SidebarContent>
                <SidebarGroup>
                    <SidebarGroupLabel>功能</SidebarGroupLabel>
                    <SidebarGroupContent>
                        <SidebarMenu>
                            {navItems.map((item) => {
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
                <div className="flex items-center justify-between px-2">
                    <span className="text-xs text-muted-foreground">
                        AI Coursework Lab
                    </span>
                    <ThemeToggle />
                </div>
            </SidebarFooter>
        </Sidebar>
    );
}
