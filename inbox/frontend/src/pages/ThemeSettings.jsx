import React, { useState } from 'react';
import { useTheme } from '../contexts/ThemeContext';
import { PRESET_THEMES } from '../utils/themeUtils';
import { 
  SwatchIcon, 
  ArrowDownTrayIcon, 
  ArrowUpTrayIcon,
  ArrowPathIcon,
  CheckIcon
} from '@heroicons/react/24/outline';

export default function ThemeSettings() {
  const { theme, applyPreset, updateColor, resetTheme, exportTheme, importTheme, isCustom } = useTheme();
  const [activeSection, setActiveSection] = useState('presets');
  const fileInputRef = React.useRef(null);

  // 处理文件导入
  const handleImport = async (e) => {
    const file = e.target.files?.[0];
    if (file) {
      const success = await importTheme(file);
      if (success) {
        alert('主题导入成功!');
      } else {
        alert('主题导入失败,请检查文件格式');
      }
    }
  };

  // 颜色选择器组件
  const ColorPicker = ({ label, value, onChange, description }) => (
    <div className="flex items-center justify-between py-3 border-b" style={{ borderColor: 'var(--color-border-primary)' }}>
      <div className="flex-1">
        <label className="block text-sm font-medium" style={{ color: 'var(--color-text-primary)' }}>
          {label}
        </label>
        {description && (
          <p className="text-xs mt-1" style={{ color: 'var(--color-text-tertiary)' }}>
            {description}
          </p>
        )}
      </div>
      <div className="flex items-center gap-3">
        <span className="text-sm font-mono" style={{ color: 'var(--color-text-secondary)' }}>
          {value}
        </span>
        <input
          type="color"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-12 h-10 rounded border cursor-pointer"
          style={{ borderColor: 'var(--color-border-primary)' }}
        />
      </div>
    </div>
  );

  return (
    <div className="min-h-screen p-6" style={{ backgroundColor: 'var(--color-bg-primary)' }}>
      <div className="max-w-6xl mx-auto">
        {/* 头部 */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2" style={{ color: 'var(--color-text-primary)' }}>
            主题设置
          </h1>
          <p style={{ color: 'var(--color-text-secondary)' }}>
            自定义界面外观,选择预设主题或创建自己的配色方案
          </p>
        </div>

        {/* 操作按钮 */}
        <div className="flex gap-3 mb-6">
          <button
            onClick={exportTheme}
            className="flex items-center gap-2 px-4 py-2 rounded-lg transition-colors"
            style={{
              backgroundColor: 'var(--color-bg-secondary)',
              color: 'var(--color-text-primary)',
              border: '1px solid var(--color-border-primary)'
            }}
            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--color-interactive-hover)'}
            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'var(--color-bg-secondary)'}
          >
            <ArrowDownTrayIcon className="h-5 w-5" />
            导出主题
          </button>
          
          <button
            onClick={() => fileInputRef.current?.click()}
            className="flex items-center gap-2 px-4 py-2 rounded-lg transition-colors"
            style={{
              backgroundColor: 'var(--color-bg-secondary)',
              color: 'var(--color-text-primary)',
              border: '1px solid var(--color-border-primary)'
            }}
            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--color-interactive-hover)'}
            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'var(--color-bg-secondary)'}
          >
            <ArrowUpTrayIcon className="h-5 w-5" />
            导入主题
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".json"
            onChange={handleImport}
            className="hidden"
          />
          
          <button
            onClick={resetTheme}
            className="flex items-center gap-2 px-4 py-2 rounded-lg transition-colors"
            style={{
              backgroundColor: 'var(--color-bg-secondary)',
              color: 'var(--color-text-primary)',
              border: '1px solid var(--color-border-primary)'
            }}
            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--color-interactive-hover)'}
            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'var(--color-bg-secondary)'}
          >
            <ArrowPathIcon className="h-5 w-5" />
            重置主题
          </button>
        </div>

        {/* 标签页 */}
        <div className="flex gap-2 mb-6 border-b" style={{ borderColor: 'var(--color-border-primary)' }}>
          {[
            { id: 'presets', label: '预设主题' },
            { id: 'background', label: '背景色' },
            { id: 'text', label: '文字颜色' },
            { id: 'accent', label: '强调色' },
            { id: 'border', label: '边框' },
            { id: 'interactive', label: '交互状态' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveSection(tab.id)}
              className="px-4 py-2 font-medium transition-colors relative"
              style={{
                color: activeSection === tab.id ? 'var(--color-accent-primary)' : 'var(--color-text-secondary)',
              }}
            >
              {tab.label}
              {activeSection === tab.id && (
                <div
                  className="absolute bottom-0 left-0 right-0 h-0.5"
                  style={{ backgroundColor: 'var(--color-accent-primary)' }}
                />
              )}
            </button>
          ))}
        </div>

        {/* 内容区域 */}
        <div className="rounded-lg p-6" style={{ backgroundColor: 'var(--color-bg-secondary)' }}>
          {/* 预设主题 */}
          {activeSection === 'presets' && (
            <div>
              <h2 className="text-xl font-semibold mb-4" style={{ color: 'var(--color-text-primary)' }}>
                选择预设主题
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {Object.entries(PRESET_THEMES).map(([key, preset]) => (
                  <button
                    key={key}
                    onClick={() => applyPreset(key)}
                    className="p-4 rounded-lg border-2 transition-all hover:scale-105"
                    style={{
                      backgroundColor: preset.colors.background.primary,
                      borderColor: theme.mode === preset.mode ? 'var(--color-accent-primary)' : preset.colors.border.primary,
                    }}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="font-semibold" style={{ color: preset.colors.text.primary }}>
                        {preset.name}
                      </h3>
                      {theme.mode === preset.mode && (
                        <CheckIcon className="h-5 w-5" style={{ color: 'var(--color-accent-primary)' }} />
                      )}
                    </div>
                    <div className="flex gap-2">
                      <div className="w-8 h-8 rounded" style={{ backgroundColor: preset.colors.accent.primary }} />
                      <div className="w-8 h-8 rounded" style={{ backgroundColor: preset.colors.accent.success }} />
                      <div className="w-8 h-8 rounded" style={{ backgroundColor: preset.colors.accent.warning }} />
                      <div className="w-8 h-8 rounded" style={{ backgroundColor: preset.colors.accent.error }} />
                    </div>
                  </button>
                ))}
              </div>
              {isCustom && (
                <div className="mt-4 p-4 rounded-lg" style={{ backgroundColor: 'var(--color-bg-tertiary)' }}>
                  <p style={{ color: 'var(--color-text-secondary)' }}>
                    ℹ️ 当前使用自定义主题配置
                  </p>
                </div>
              )}
            </div>
          )}

          {/* 背景色设置 */}
          {activeSection === 'background' && (
            <div>
              <h2 className="text-xl font-semibold mb-4" style={{ color: 'var(--color-text-primary)' }}>
                背景颜色
              </h2>
              <ColorPicker
                label="主背景色"
                value={theme.colors.background.primary}
                onChange={(val) => updateColor('background.primary', val)}
                description="页面主要背景色"
              />
              <ColorPicker
                label="次要背景色"
                value={theme.colors.background.secondary}
                onChange={(val) => updateColor('background.secondary', val)}
                description="卡片、面板背景色"
              />
              <ColorPicker
                label="三级背景色"
                value={theme.colors.background.tertiary}
                onChange={(val) => updateColor('background.tertiary', val)}
                description="输入框、下拉菜单背景色"
              />
              <ColorPicker
                label="弹窗背景色"
                value={theme.colors.background.modal}
                onChange={(val) => updateColor('background.modal', val)}
                description="模态框、对话框背景色"
              />
            </div>
          )}

          {/* 文字颜色设置 */}
          {activeSection === 'text' && (
            <div>
              <h2 className="text-xl font-semibold mb-4" style={{ color: 'var(--color-text-primary)' }}>
                文字颜色
              </h2>
              <ColorPicker
                label="主要文字"
                value={theme.colors.text.primary}
                onChange={(val) => updateColor('text.primary', val)}
                description="标题、正文等主要文字"
              />
              <ColorPicker
                label="次要文字"
                value={theme.colors.text.secondary}
                onChange={(val) => updateColor('text.secondary', val)}
                description="辅助说明、描述文字"
              />
              <ColorPicker
                label="三级文字"
                value={theme.colors.text.tertiary}
                onChange={(val) => updateColor('text.tertiary', val)}
                description="占位符、禁用文字"
              />
              <ColorPicker
                label="反色文字"
                value={theme.colors.text.inverse}
                onChange={(val) => updateColor('text.inverse', val)}
                description="按钮上的文字等反色场景"
              />
            </div>
          )}

          {/* 强调色设置 */}
          {activeSection === 'accent' && (
            <div>
              <h2 className="text-xl font-semibold mb-4" style={{ color: 'var(--color-text-primary)' }}>
                强调色
              </h2>
              <ColorPicker
                label="主要强调色"
                value={theme.colors.accent.primary}
                onChange={(val) => updateColor('accent.primary', val)}
                description="主按钮、链接、选中状态"
              />
              <ColorPicker
                label="成功色"
                value={theme.colors.accent.success}
                onChange={(val) => updateColor('accent.success', val)}
                description="成功提示、正向操作"
              />
              <ColorPicker
                label="警告色"
                value={theme.colors.accent.warning}
                onChange={(val) => updateColor('accent.warning', val)}
                description="警告提示、需注意的信息"
              />
              <ColorPicker
                label="错误色"
                value={theme.colors.accent.error}
                onChange={(val) => updateColor('accent.error', val)}
                description="错误提示、危险操作"
              />
              <ColorPicker
                label="信息色"
                value={theme.colors.accent.info}
                onChange={(val) => updateColor('accent.info', val)}
                description="信息提示、中性操作"
              />
            </div>
          )}

          {/* 边框设置 */}
          {activeSection === 'border' && (
            <div>
              <h2 className="text-xl font-semibold mb-4" style={{ color: 'var(--color-text-primary)' }}>
                边框颜色
              </h2>
              <ColorPicker
                label="主要边框"
                value={theme.colors.border.primary}
                onChange={(val) => updateColor('border.primary', val)}
                description="卡片边框、分隔线"
              />
              <ColorPicker
                label="次要边框"
                value={theme.colors.border.secondary}
                onChange={(val) => updateColor('border.secondary', val)}
                description="输入框边框、细分隔线"
              />
            </div>
          )}

          {/* 交互状态设置 */}
          {activeSection === 'interactive' && (
            <div>
              <h2 className="text-xl font-semibold mb-4" style={{ color: 'var(--color-text-primary)' }}>
                交互状态颜色
              </h2>
              <ColorPicker
                label="悬停状态"
                value={theme.colors.interactive.hover}
                onChange={(val) => updateColor('interactive.hover', val)}
                description="鼠标悬停时的背景色"
              />
              <ColorPicker
                label="激活状态"
                value={theme.colors.interactive.active}
                onChange={(val) => updateColor('interactive.active', val)}
                description="点击、选中时的背景色"
              />
              <ColorPicker
                label="聚焦状态"
                value={theme.colors.interactive.focus}
                onChange={(val) => updateColor('interactive.focus', val)}
                description="输入框聚焦时的边框色"
              />
            </div>
          )}
        </div>

        {/* 实时预览 */}
        <div className="mt-8 rounded-lg p-6" style={{ backgroundColor: 'var(--color-bg-secondary)' }}>
          <h2 className="text-xl font-semibold mb-4" style={{ color: 'var(--color-text-primary)' }}>
            实时预览
          </h2>
          <div className="space-y-4">
            {/* 按钮预览 */}
            <div>
              <p className="text-sm mb-2" style={{ color: 'var(--color-text-secondary)' }}>按钮</p>
              <div className="flex gap-3">
                <button
                  className="px-4 py-2 rounded-lg font-medium"
                  style={{
                    backgroundColor: 'var(--color-accent-primary)',
                    color: 'var(--color-text-inverse)',
                  }}
                >
                  主要按钮
                </button>
                <button
                  className="px-4 py-2 rounded-lg font-medium"
                  style={{
                    backgroundColor: 'var(--color-accent-success)',
                    color: 'var(--color-text-inverse)',
                  }}
                >
                  成功按钮
                </button>
                <button
                  className="px-4 py-2 rounded-lg font-medium"
                  style={{
                    backgroundColor: 'var(--color-accent-warning)',
                    color: 'var(--color-text-inverse)',
                  }}
                >
                  警告按钮
                </button>
                <button
                  className="px-4 py-2 rounded-lg font-medium"
                  style={{
                    backgroundColor: 'var(--color-accent-error)',
                    color: 'var(--color-text-inverse)',
                  }}
                >
                  错误按钮
                </button>
              </div>
            </div>

            {/* 卡片预览 */}
            <div>
              <p className="text-sm mb-2" style={{ color: 'var(--color-text-secondary)' }}>卡片</p>
              <div
                className="p-4 rounded-lg border"
                style={{
                  backgroundColor: 'var(--color-bg-tertiary)',
                  borderColor: 'var(--color-border-primary)',
                }}
              >
                <h3 className="font-semibold mb-2" style={{ color: 'var(--color-text-primary)' }}>
                  卡片标题
                </h3>
                <p style={{ color: 'var(--color-text-secondary)' }}>
                  这是卡片的内容文字,用于展示主题效果。
                </p>
                <p className="text-sm mt-2" style={{ color: 'var(--color-text-tertiary)' }}>
                  辅助说明文字
                </p>
              </div>
            </div>

            {/* 输入框预览 */}
            <div>
              <p className="text-sm mb-2" style={{ color: 'var(--color-text-secondary)' }}>输入框</p>
              <input
                type="text"
                placeholder="输入框示例"
                className="w-full px-4 py-2 rounded-lg border outline-none focus:ring-2"
                style={{
                  backgroundColor: 'var(--color-bg-tertiary)',
                  borderColor: 'var(--color-border-primary)',
                  color: 'var(--color-text-primary)',
                }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
