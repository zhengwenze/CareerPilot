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
        <Label className="text-black">{label}</Label>
        <Button
          className="rounded-full border-black/10 bg-white text-black hover:bg-[#f5f5f7]"
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
          <div className="rounded-[1.5rem] border border-dashed border-black/12 bg-white px-4 py-4 text-sm text-black/58">
            暂无内容，点击“新增”补充。
          </div>
        ) : null}
        {items.map((item, index) => (
          <div className="flex gap-3" key={`${label}-${index}`}>
            <Textarea
              className="min-h-20 rounded-2xl border-black/10 bg-[#f5f5f7] text-black placeholder:text-black/40 focus-visible:border-[#0071E3] focus-visible:ring-[#0071E3]/20"
              onChange={(event) => {
                const nextItems = [...items];
                nextItems[index] = event.target.value;
                onChange(nextItems);
              }}
              placeholder={placeholder}
              value={item}
            />
            <Button
              className="shrink-0 rounded-2xl border-black/10 bg-white text-black hover:bg-[#f5f5f7]"
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
    <Card className="rounded-[2rem] border border-black/10 bg-white py-0 shadow-[0_18px_48px_rgba(0,0,0,0.05)]">
      <CardHeader className="px-6 py-6">
        <CardTitle className="text-2xl font-semibold tracking-[-0.04em] text-black">
          结构化结果编辑
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6 px-6 pb-6">
        <div className="grid gap-4 md:grid-cols-2">
          <div className="grid gap-2">
            <Label htmlFor="resume-name" className="text-black">姓名</Label>
            <Input
              className="h-12 rounded-2xl border-black/10 bg-[#f5f5f7] px-4 text-black focus-visible:border-[#0071E3] focus-visible:ring-[#0071E3]/20"
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
            <Label htmlFor="resume-email" className="text-black">邮箱</Label>
            <Input
              className="h-12 rounded-2xl border-black/10 bg-[#f5f5f7] px-4 text-black focus-visible:border-[#0071E3] focus-visible:ring-[#0071E3]/20"
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
            <Label htmlFor="resume-phone" className="text-black">手机号</Label>
            <Input
              className="h-12 rounded-2xl border-black/10 bg-[#f5f5f7] px-4 text-black focus-visible:border-[#0071E3] focus-visible:ring-[#0071E3]/20"
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
            <Label htmlFor="resume-location" className="text-black">地点</Label>
            <Input
              className="h-12 rounded-2xl border-black/10 bg-[#f5f5f7] px-4 text-black focus-visible:border-[#0071E3] focus-visible:ring-[#0071E3]/20"
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
          <Label htmlFor="resume-summary" className="text-black">摘要</Label>
          <Textarea
            className="rounded-2xl border-black/10 bg-[#f5f5f7] text-black focus-visible:border-[#0071E3] focus-visible:ring-[#0071E3]/20"
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
            <Label htmlFor="skills-technical" className="text-black">技术技能</Label>
            <Input
              className="h-12 rounded-2xl border-black/10 bg-[#f5f5f7] px-4 text-black placeholder:text-black/40 focus-visible:border-[#0071E3] focus-visible:ring-[#0071E3]/20"
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
            <Label htmlFor="skills-tools" className="text-black">工具技能</Label>
            <Input
              className="h-12 rounded-2xl border-black/10 bg-[#f5f5f7] px-4 text-black placeholder:text-black/40 focus-visible:border-[#0071E3] focus-visible:ring-[#0071E3]/20"
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
            <Label htmlFor="skills-languages" className="text-black">语言能力</Label>
            <Input
              className="h-12 rounded-2xl border-black/10 bg-[#f5f5f7] px-4 text-black placeholder:text-black/40 focus-visible:border-[#0071E3] focus-visible:ring-[#0071E3]/20"
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
