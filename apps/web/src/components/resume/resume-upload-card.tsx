"use client";

import { useRef } from "react";
import { FileUp } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function ResumeUploadCard({
  isUploading,
  onUpload,
}: {
  isUploading: boolean;
  onUpload: (file: File) => void;
}) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  return (
    <Card className="surface-card border-0 bg-card/82 py-0 shadow-xl shadow-emerald-950/6">
      <CardHeader className="px-5 py-5">
        <Badge className="w-fit bg-primary/10 text-primary hover:bg-primary/10">
          Upload
        </Badge>
        <CardTitle className="text-xl font-semibold text-foreground">
          上传 PDF 简历
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 px-5 pb-5">
        <p className="text-sm leading-7 text-muted-foreground">
          上传后会自动进入解析流程，系统会抽取文本并生成可人工修正的结构化结果。
        </p>

        <input
          accept="application/pdf,.pdf"
          className="hidden"
          disabled={isUploading}
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (!file) {
              return;
            }

            onUpload(file);
            event.currentTarget.value = "";
          }}
          ref={fileInputRef}
          type="file"
        />
        <Button
          className="w-full rounded-full"
          disabled={isUploading}
          onClick={() => fileInputRef.current?.click()}
          type="button"
          variant="default"
        >
          {isUploading ? "上传中..." : "选择 PDF 文件"}
          <FileUp className="size-4" />
        </Button>
      </CardContent>
    </Card>
  );
}
