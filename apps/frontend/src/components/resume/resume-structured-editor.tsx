"use client";

import { Plus, X } from "lucide-react";

import { Button } from "@/components/ui/button";
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
        <Label className="font-mono text-xs font-bold uppercase text-black">
          {label}
        </Label>
        <Button
          onClick={() => onChange([...items, ""])}
          size="sm"
          type="button"
          variant="secondary"
        >
          新增
          <Plus className="ml-2 size-4" />
        </Button>
      </div>
      <div className="space-y-3">
        {items.length === 0 ? (
          <div className="border-2 border-dashed border-black bg-white p-4 font-mono text-sm text-black">
            暂无内容，点击&quot;新增&quot;补充。
          </div>
        ) : null}
        {items.map((item, index) => (
          <div className="flex gap-3" key={`${label}-${index}`}>
            <Textarea
              className="min-h-20 border-2 border-black bg-white font-mono text-sm text-black placeholder:text-black/40 focus:bg-[#ffffcc]"
              onChange={(event) => {
                const nextItems = [...items];
                nextItems[index] = event.target.value;
                onChange(nextItems);
              }}
              placeholder={placeholder}
              value={item}
            />
            <Button
              onClick={() => onChange(items.filter((_, itemIndex) => itemIndex !== index))}
              size="icon"
              type="button"
              variant="secondary"
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
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2">
        <div className="grid gap-2">
          <Label className="font-mono text-xs font-bold uppercase text-black" htmlFor="resume-name">
            姓名
          </Label>
          <Input
            className="border-2 border-black bg-white text-black"
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
          <Label className="font-mono text-xs font-bold uppercase text-black" htmlFor="resume-email">
            邮箱
          </Label>
          <Input
            className="border-2 border-black bg-white text-black"
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
          <Label className="font-mono text-xs font-bold uppercase text-black" htmlFor="resume-phone">
            手机号
          </Label>
          <Input
            className="border-2 border-black bg-white text-black"
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
          <Label className="font-mono text-xs font-bold uppercase text-black" htmlFor="resume-location">
            地点
          </Label>
          <Input
            className="border-2 border-black bg-white text-black"
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
        <Label className="font-mono text-xs font-bold uppercase text-black" htmlFor="resume-summary">
          摘要
        </Label>
        <Textarea
          className="border-2 border-black bg-white font-mono text-sm text-black focus:bg-[#ffffcc]"
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
          <Label className="font-mono text-xs font-bold uppercase text-black" htmlFor="skills-technical">
            技术技能
          </Label>
          <Input
            className="border-2 border-black bg-white font-mono text-sm text-black placeholder:text-black/40"
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
          <Label className="font-mono text-xs font-bold uppercase text-black" htmlFor="skills-tools">
            工具技能
          </Label>
          <Input
            className="border-2 border-black bg-white font-mono text-sm text-black placeholder:text-black/40"
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
          <Label className="font-mono text-xs font-bold uppercase text-black" htmlFor="skills-languages">
            语言能力
          </Label>
          <Input
            className="border-2 border-black bg-white font-mono text-sm text-black placeholder:text-black/40"
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
    </div>
  );
}
