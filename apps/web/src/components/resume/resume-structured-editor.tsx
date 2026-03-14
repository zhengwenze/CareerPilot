"use client";

import { Plus, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import type { ResumeStructuredData } from "@/lib/api/modules/resume";

function StructuredListEditor({
  label,
  items,
  onChange,
  placeholder,
}: {
  label: string;
  items: string[];
  onChange: (items: string[]) => void;
  placeholder: string;
}) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <Label>{label}</Label>
        <Button
          className="rounded-full"
          onClick={() => onChange([...items, ""])}
          size="sm"
          type="button"
          variant="outline"
        >
          新增
          <Plus className="size-4" />
        </Button>
      </div>
      <div className="space-y-3">
        {items.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-border/70 px-4 py-4 text-sm text-muted-foreground">
            暂无内容，点击“新增”补充。
          </div>
        ) : null}
        {items.map((item, index) => (
          <div className="flex gap-3" key={`${label}-${index}`}>
            <Textarea
              className="min-h-20 rounded-2xl border-border/70 bg-white/80"
              onChange={(event) => {
                const nextItems = [...items];
                nextItems[index] = event.target.value;
                onChange(nextItems);
              }}
              placeholder={placeholder}
              value={item}
            />
            <Button
              className="shrink-0 rounded-2xl"
              onClick={() => onChange(items.filter((_, itemIndex) => itemIndex !== index))}
              size="icon"
              type="button"
              variant="outline"
            >
              <X className="size-4" />
            </Button>
          </div>
        ))}
      </div>
    </div>
  );
}

function toCommaValue(items: string[]) {
  return items.join(", ");
}

function fromCommaValue(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function ResumeStructuredEditor({
  value,
  onChange,
}: {
  value: ResumeStructuredData;
  onChange: (value: ResumeStructuredData) => void;
}) {
  return (
    <Card className="surface-card border-0 bg-card/82 py-0 shadow-xl shadow-emerald-950/5">
      <CardHeader className="px-6 py-6">
        <CardTitle className="text-2xl font-semibold text-foreground">
          结构化结果编辑
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6 px-6 pb-6">
        <div className="grid gap-4 md:grid-cols-2">
          <div className="grid gap-2">
            <Label htmlFor="resume-name">姓名</Label>
            <Input
              className="h-11 rounded-2xl border-border/70 bg-white/80 px-4"
              id="resume-name"
              onChange={(event) =>
                onChange({
                  ...value,
                  basic_info: {
                    ...value.basic_info,
                    name: event.target.value,
                  },
                })
              }
              value={value.basic_info.name}
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="resume-email">邮箱</Label>
            <Input
              className="h-11 rounded-2xl border-border/70 bg-white/80 px-4"
              id="resume-email"
              onChange={(event) =>
                onChange({
                  ...value,
                  basic_info: {
                    ...value.basic_info,
                    email: event.target.value,
                  },
                })
              }
              value={value.basic_info.email}
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="resume-phone">手机号</Label>
            <Input
              className="h-11 rounded-2xl border-border/70 bg-white/80 px-4"
              id="resume-phone"
              onChange={(event) =>
                onChange({
                  ...value,
                  basic_info: {
                    ...value.basic_info,
                    phone: event.target.value,
                  },
                })
              }
              value={value.basic_info.phone}
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="resume-location">地点</Label>
            <Input
              className="h-11 rounded-2xl border-border/70 bg-white/80 px-4"
              id="resume-location"
              onChange={(event) =>
                onChange({
                  ...value,
                  basic_info: {
                    ...value.basic_info,
                    location: event.target.value,
                  },
                })
              }
              value={value.basic_info.location}
            />
          </div>
        </div>

        <div className="grid gap-2">
          <Label htmlFor="resume-summary">摘要</Label>
          <Textarea
            className="rounded-2xl border-border/70 bg-white/80"
            id="resume-summary"
            onChange={(event) =>
              onChange({
                ...value,
                basic_info: {
                  ...value.basic_info,
                  summary: event.target.value,
                },
              })
            }
            value={value.basic_info.summary}
          />
        </div>

        <StructuredListEditor
          items={value.education}
          label="教育经历"
          onChange={(items) => onChange({ ...value, education: items })}
          placeholder="例如：复旦大学 - 计算机科学与技术"
        />

        <StructuredListEditor
          items={value.work_experience}
          label="工作经历"
          onChange={(items) => onChange({ ...value, work_experience: items })}
          placeholder="例如：CareerPilot - 前端实习生"
        />

        <StructuredListEditor
          items={value.projects}
          label="项目经历"
          onChange={(items) => onChange({ ...value, projects: items })}
          placeholder="例如：简历平台重构项目"
        />

        <StructuredListEditor
          items={value.certifications}
          label="证书与奖项"
          onChange={(items) => onChange({ ...value, certifications: items })}
          placeholder="例如：英语六级 / PMP"
        />

        <div className="grid gap-4 md:grid-cols-3">
          <div className="grid gap-2">
            <Label htmlFor="skills-technical">技术技能</Label>
            <Input
              className="h-11 rounded-2xl border-border/70 bg-white/80 px-4"
              id="skills-technical"
              onChange={(event) =>
                onChange({
                  ...value,
                  skills: {
                    ...value.skills,
                    technical: fromCommaValue(event.target.value),
                  },
                })
              }
              placeholder="Python, React, SQL"
              value={toCommaValue(value.skills.technical)}
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="skills-tools">工具技能</Label>
            <Input
              className="h-11 rounded-2xl border-border/70 bg-white/80 px-4"
              id="skills-tools"
              onChange={(event) =>
                onChange({
                  ...value,
                  skills: {
                    ...value.skills,
                    tools: fromCommaValue(event.target.value),
                  },
                })
              }
              placeholder="Docker, Git, Figma"
              value={toCommaValue(value.skills.tools)}
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="skills-languages">语言能力</Label>
            <Input
              className="h-11 rounded-2xl border-border/70 bg-white/80 px-4"
              id="skills-languages"
              onChange={(event) =>
                onChange({
                  ...value,
                  skills: {
                    ...value.skills,
                    languages: fromCommaValue(event.target.value),
                  },
                })
              }
              placeholder="English, 日语"
              value={toCommaValue(value.skills.languages)}
            />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
