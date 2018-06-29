ckan.module('export-page-to-png', function($) {
    return {
        initialize: function() {
            this.el.click(function(e){
                e.preventDefault()
                this.downloadMap()
            }.bind(this))
        },
        downloadMap: function() {
            var scrollY = window.pageYOffset;
            var container = document.body;
            var className = 'c3chart'
            window.scrollTo(0, 0);
            //fix weird back fill
            d3.select('.' + className).selectAll("path").attr("fill", "none");
            //fix no axes
            d3.select('.' + className).selectAll("path.domain").attr("stroke", "black");
            //fix no tick
            d3.select('.' + className).selectAll(".tick line").attr("stroke", "black");
           
            html2canvas(container, {
                allowTaint: true,
                useCORS: true,
                foreignObjectRendering: true,
                ignoreElements: function(element) {
                    return false
                }
            }).then(function(canvas) {
                var a = document.createElement('a')
                a.href = canvas.toDataURL()
                a.download = 'chart.png'
                document.body.appendChild(a)
                a.click()
                document.body.removeChild(a)          
            });
            window.scrollTo(0, scrollY);
        }
    }
})