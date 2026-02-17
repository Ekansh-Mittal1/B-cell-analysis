<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import * as d3 from 'd3';
  import type { LongitudinalGroupData } from '../../utils/repertoire-metrics';

  export let data: LongitudinalGroupData[] = [];
  export let topN = 10;

  let container: HTMLDivElement;
  let width = 500;
  let ro: ResizeObserver;

  onMount(() => {
    ro = new ResizeObserver((entries) => {
      for (const entry of entries) width = entry.contentRect.width;
    });
    ro.observe(container);
  });
  onDestroy(() => { ro?.disconnect(); });

  $: if (container && data.length > 0) drawChart(data, width);

  const PALETTE = [
    '#0066CC', '#E85D04', '#2D9F3F', '#9B59B6', '#E74C3C',
    '#00ACC1', '#F39C12', '#7F8C8D', '#3498DB', '#E67E22'
  ];

  function drawChart(groups: LongitudinalGroupData[], w: number) {
    if (!container) return;
    const svg = d3.select(container).select('svg');
    svg.selectAll('*').remove();

    const margin = { top: 28, right: 100, bottom: 40, left: 55 };
    const chartH = 250;
    const totalH = groups.length * (chartH + 30) + 10;
    const innerW = w - margin.left - margin.right;

    svg.attr('width', w).attr('height', totalH);

    groups.forEach((grp, gi) => {
      const g = svg.append('g')
        .attr('transform', `translate(${margin.left}, ${gi * (chartH + 30) + margin.top})`);
      const innerH = chartH - margin.top - margin.bottom;

      g.append('text').attr('x', 0).attr('y', -10)
        .style('font-size', '13px').style('font-weight', '600').style('fill', grp.groupColor)
        .text(`${grp.groupName} — SHM Accumulation (persistent clones)`);

      // Only show persistent clones that have SHM data
      const persistent = grp.trackedClones
        .filter(c => c.persistent && c.meanSHM.some(v => v > 0))
        .slice(0, topN);

      if (persistent.length === 0) {
        g.append('text').attr('x', innerW / 2).attr('y', innerH / 2)
          .attr('text-anchor', 'middle').style('fill', '#9BA3AF').style('font-size', '12px')
          .text('No persistent clones with SHM data');
        return;
      }

      const labels = grp.timepointLabels;
      const x = d3.scalePoint<string>().domain(labels).range([0, innerW]).padding(0.3);
      const yMax = d3.max(persistent.flatMap(c => c.meanSHM)) || 1;
      const y = d3.scaleLinear().domain([0, yMax * 1.15]).nice().range([innerH, 0]);

      g.append('g').attr('transform', `translate(0,${innerH})`)
        .call(d3.axisBottom(x)).selectAll('text').style('font-size', '10px');
      g.append('g').call(d3.axisLeft(y).ticks(5))
        .selectAll('text').style('font-size', '10px');
      g.append('g')
        .call(d3.axisLeft(y).ticks(5).tickSize(-innerW).tickFormat(() => ''))
        .selectAll('line').style('stroke', '#E8EAED').style('stroke-dasharray', '3,3');
      g.selectAll('.domain').remove();

      g.append('text')
        .attr('transform', 'rotate(-90)')
        .attr('x', -innerH / 2).attr('y', -42)
        .attr('text-anchor', 'middle')
        .style('font-size', '11px').style('fill', '#6B7280')
        .text('Mean SHM');

      const line = d3.line<number>()
        .x((_: any, i: number) => x(labels[i]) ?? 0)
        .y((d: any) => y(d))
        .curve(d3.curveMonotoneX);

      persistent.forEach((clone, ci) => {
        const color = PALETTE[ci % PALETTE.length];
        g.append('path')
          .datum(clone.meanSHM)
          .attr('fill', 'none')
          .attr('stroke', color)
          .attr('stroke-width', 2)
          .attr('opacity', 0.8)
          .attr('d', line);

        clone.meanSHM.forEach((v, i) => {
          g.append('circle')
            .attr('cx', x(labels[i]) ?? 0)
            .attr('cy', y(v))
            .attr('r', 3)
            .attr('fill', color)
            .attr('stroke', '#fff')
            .attr('stroke-width', 1);
        });

        // Right label
        const lastVal = clone.meanSHM[clone.meanSHM.length - 1];
        g.append('text')
          .attr('x', innerW + 6)
          .attr('y', y(lastVal) + 3)
          .style('font-size', '9px').style('fill', color)
          .text(`Clone ${clone.cloneId}`);
      });
    });
  }
</script>

<div class="chart-wrapper" bind:this={container}>
  <svg></svg>
</div>

<style>
  .chart-wrapper {
    position: relative;
    width: 100%;
    min-height: 260px;
  }
</style>
