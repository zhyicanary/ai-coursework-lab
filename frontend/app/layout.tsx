"use client";

import { Inter } from "next/font/google";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Brain, Search, Plane, Settings, Moon, Sun } from "lucide-react";
import { useState, useEffect } from "react";
import {
    SidebarProvider,
    SidebarInset,
    SidebarTrigger,
} from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/app-sidebar";
import { Separator } from "@/components/ui/separator";
import {
    Breadcrumb,
    BreadcrumbItem,
    BreadcrumbLink,
    BreadcrumbList,
    BreadcrumbPage,
    BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import { Toaster } from "@/components/ui/sonner";
import { KnowSeekerProvider } from "@/lib/knowseeker-context";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

const navItems = [
    { href: "/", label: "首页", icon: Brain },
    { href: "/knowseeker", label: "KnowSeeker", icon: Search },
    { href: "/tripmind", label: "TripMind", icon: Plane },
    { href: "/settings", label: "设置", icon: Settings },
];

function ThemeToggle() {
    const [dark, setDark] = useState(false);

    useEffect(() => {
        const stored = localStorage.getItem("theme");
        if (
            stored === "dark" ||
            (!stored && window.matchMedia("(prefers-color-scheme: dark)").matches)
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
        <Button variant="ghost" size="icon" onClick={toggle} className="size-8">
            {dark ? <Sun className="size-4" /> : <Moon className="size-4" />}
        </Button>
    );
}

function getBreadcrumb(pathname: string) {
    const item = navItems.find((n) => n.href === pathname);
    if (!item) return [{ label: "首页", href: "/" }];
    if (pathname === "/") return [{ label: "首页", href: "/" }];
    return [
        { label: "首页", href: "/" },
        { label: item.label, href: pathname },
    ];
}

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const pathname = usePathname();
    const breadcrumbs = getBreadcrumb(pathname);

    return (
        <html lang="zh-CN" suppressHydrationWarning>
            <body className={inter.className}>
                <KnowSeekerProvider>
                <SidebarProvider defaultOpen>
                    <AppSidebar />
                    <SidebarInset>
                        <header className="sticky top-0 z-40 flex h-14 shrink-0 items-center gap-2 border-b bg-background/80 backdrop-blur-sm px-4">
                            <SidebarTrigger className="-ml-1" />
                            <Separator
                                orientation="vertical"
                                className="mr-2 h-4"
                            />
                            <Breadcrumb>
                                <BreadcrumbList>
                                    {breadcrumbs.map((bc, i) => (
                                        <div
                                            key={bc.href}
                                            className="flex items-center gap-2"
                                        >
                                            {i > 0 && (
                                                <BreadcrumbSeparator className="hidden md:block" />
                                            )}
                                            <BreadcrumbItem>
                                                {i === breadcrumbs.length - 1 ? (
                                                    <BreadcrumbPage>
                                                        {bc.label}
                                                    </BreadcrumbPage>
                                                ) : (
                                                    <BreadcrumbLink asChild>
                                                        <Link href={bc.href}>
                                                            {bc.label}
                                                        </Link>
                                                    </BreadcrumbLink>
                                                )}
                                            </BreadcrumbItem>
                                        </div>
                                    ))}
                                </BreadcrumbList>
                            </Breadcrumb>
                            <div className="ml-auto flex items-center gap-2">
                                <Link
                                    href="/"
                                    className="flex items-center gap-1.5 text-sm font-semibold md:hidden"
                                >
                                    <Brain className="size-4 text-primary" />
                                </Link>
                                <ThemeToggle />
                            </div>
                        </header>
                        <main className="flex-1">{children}</main>
                    </SidebarInset>
                </SidebarProvider>
                </KnowSeekerProvider>
                <Toaster />
            </body>
        </html>
    );
}
