function renderPlayerStats(skillHistory, wins, losses) {
    var outerWidth = $("#rating_history").width();
    var outerHeight = $("#rating_history").height();

    var margin = {top: 10, right: 10, bottom: 60, left: 35};

    d3.select("#rating_history_svg").remove();

    var svg = d3
        .select("#rating_history")
        .append("svg")
        .attr("id", "rating_history_svg")
        .attr("width", "100%")
        .attr("height", "100%")
        .attr("preserveAspectRatio", "xMinYMin meet")
        .attr("viewBox", "0 0 " + outerWidth + " " + outerHeight)
        .classed("svg-content", true)
        .append("g")
        .attr("transform", "translate(" + margin.left + "," + margin.top + ")");

    var width = outerWidth - margin.left - margin.right;
    var height = outerHeight - margin.top - margin.bottom;

    var timeDomain = d3.extent(skillHistory, d => d[0])
    var timeDomainHasZeroExtent = timeDomain[0] == timeDomain[1]
    // If time domain has zero extent, expand it by one month on either side
    if (timeDomainHasZeroExtent) {
        timeDomain[0] = new Date(
            timeDomain[0].getFullYear(),
            timeDomain[0].getMonth() - 1,
            timeDomain[0].getDate());
        timeDomain[1] = new Date(
            timeDomain[1].getFullYear(),
            timeDomain[1].getMonth() + 1,
            timeDomain[1].getDate());
    }
    var xScale = d3.scaleTime()
        .domain(timeDomain)
        .range([0, width]);

    var yScale = d3.scaleLinear()
        .domain([
            Math.min(
                d3.min(skillHistory, d => d[2]),
                d3.min(wins, d => d[1]),
                d3.min(losses, d => d[1])),
            Math.max(
                d3.max(skillHistory, d => d[3]),
                d3.max(wins, d => d[1]),
                d3.max(losses, d => d[1]))]).nice()
        .range([height, 0]);

    // X gridlines
    svg.append("g")
        .attr("class", "grid")
        .attr("transform", "translate(0," + height + ")")
        .call(d3.axisBottom(xScale)
              .tickSize(-height)
              .tickFormat(""));

    // Y gridlines
    svg.append("g")
        .attr("class", "grid")
        .call(d3.axisLeft(yScale)
              .tickSize(-width)
              .tickFormat(""));

    // X axis
    svg.append("g")
        .attr("class", "x axis")
        .attr("transform", "translate(0," + height + ")")
        .call(d3.axisBottom(xScale))
        .selectAll("text")
        .style("text-anchor", "end")
        .attr("dx", "-.8em")
        .attr("dy", ".15em")
        .attr("transform", "rotate(-35)");

    // Y axis
    svg.append("g")
        .attr("class", "y axis")
        .call(d3.axisLeft(yScale));

    // Skill confidence interval
    if (!timeDomainHasZeroExtent) {
        var skill_interval = d3
            .area()
            .x(d => xScale(d[0]))
            .y0(d => yScale(d[2]))
            .y1(d => yScale(d[3]));

        svg.append("path")
            .datum(skillHistory)
            .attr("class", "skill_interval")
            .attr("d", skill_interval);
    } else {
        // An area plot would be invisible, so use a rectangle of specified width instead
        svg.selectAll("rect.skill_interval")
            .data(skillHistory)
            .enter()
            .append("rect")
            .attr("class", "skill_interval")
            .attr("x", d =>
                  xScale(new Date(d[0].getFullYear(), d[0].getMonth(), d[0].getDate() - 1)))
            .attr("y", d => yScale(d[3]))
            .attr("width", d =>
                  (xScale(new Date(d[0].getFullYear(), d[0].getMonth(), d[0].getDate() + 1))
                   - xScale(new Date(d[0].getFullYear(), d[0].getMonth(), d[0].getDate() - 1))))
            .attr("height", d => yScale(d[2]) - yScale(d[3]))
    }

    // Skill line
    var skill_line = d3.line()
        .x(d => xScale(d[0]))
        .y(d => yScale(d[1]));

    svg.append("path")
        .datum(skillHistory)
        .attr("class", "skill_line")
        .attr("d", skill_line);

    // Skill points
    var monthNames = [
        "January", "February", "March",
        "April", "May", "June", "July",
        "August", "September", "October",
        "November", "December"
    ];
    var skillPoints = svg.selectAll(".skill_point")
        .data(skillHistory)
        .enter().append("circle")
        .attr("class", d => "skill_point")
        .attr("cx", d => xScale(d[0]))
        .attr("cy", d => yScale(d[1]))
        .attr("data-x", d => xScale(d[0]))
        .attr("data-y", d => yScale(d[1]))
        .attr("data-label",
              d =>
              ("<b>"
               + monthNames[d[0].getMonth()]
               + " "
               + d[0].getFullYear()
               + "</b><br/>Rating: <b>"
               + d[1].toFixed(3)
               + "</b> \u00B1 <b>"
               + ((d[3] - d[2]) / 6.0).toFixed(3) // extract the standard
                                                  // deviation of the interval
               + "</b>"))
        .attr("r", 2);

    var triangle = d3.symbol()
        .type(d3.symbolTriangle)
        .size(25);

    var winPoints = svg.selectAll(".win_point")
        .data(wins)
        .enter().append("path")
        .attr("d", triangle)
        .attr("class", d => "win_point")
        .attr("transform", d => "translate(" + xScale(d[0]) + "," + yScale(d[1]) + ")")
        .attr("data-x", d => xScale(d[0]))
        .attr("data-y", d => yScale(d[1]))
        .attr("data-label", d => d[2] + " (" + d[1].toFixed(2) + ")");

    var invertedTriangle = d3.symbol()
        .type(d3.symbolTriangle)
        .size(25);

    var lossPoints = svg.selectAll(".loss_point")
        .data(losses)
        .enter().append("path")
        .attr("d", invertedTriangle)
        .attr("class", d => "loss_point")
        .attr("transform", d => "translate(" + xScale(d[0]) + "," + yScale(d[1]) + ") rotate(180)")
        .attr("data-x", d => xScale(d[0]))
        .attr("data-y", d => yScale(d[1]))
        .attr("data-label", d => d[2] + " (" + d[1].toFixed(2) + ")");

    // Skill points hover with Voronoi
    var voronoi = d3.voronoi()
        .x(p => p.getAttribute("data-x"))
        .y(p => p.getAttribute("data-y"))
        .extent([[0, 0], [width, height]]);

    var voronoiGroup = svg
        .append("g")
        .attr("class", "voronoi");

    voronoiGroup.selectAll("path")
        .data(voronoi.polygons(skillPoints.nodes().concat(winPoints.nodes(), lossPoints.nodes())))
        .enter().append("path")
        .attr("d", function(d) { return d ? "M" + d.join("L") + "Z" : null; })
        .style("fill", "none")
    // .style("stroke", "#2074A0")
        .style("pointer-events", "all")
        .on("mouseover", showTooltip)
        .on("mouseout",  removeTooltip);
}

function showTooltip(d) {
    $(d.data).popover({
        placement: 'auto',
        container: '#rating_history',
        trigger: 'manual',
        html: true,
        content: d.data.getAttribute("data-label"),
    });
    $(d.data).popover('show');
}

function removeTooltip(d) {
    $(d.data).popover('dispose');
}
